"""
Tests for JobEngine.

Run:
    pip install pytest pytest-asyncio httpx --break-system-packages
    pytest tests/ -v
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.database import Base
from app.models.vacancy import Vacancy
from app.services.vacancy_service import VacancyService
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource
from app.main import app, get_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite database for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client with overridden DB."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def make_vacancy(n=1, source=JobSource.DJINNI) -> VacancyCreate:
    return VacancyCreate(
        title=f"Python Developer #{n}",
        company=f"Company {n}",
        url=f"https://djinni.co/jobs/{n}/",
        description=f"We need Python dev #{n}. FastAPI, PostgreSQL.",
        source=source,
        salary="$2000-3000",
    )


# ── VacancyService tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_vacancy(db_session):
    service = VacancyService(db_session)
    vacancy = await service.create_vacancy(make_vacancy(1))

    assert vacancy is not None
    assert vacancy.id is not None
    assert vacancy.title == "Python Developer #1"
    assert vacancy.is_analyzed is False
    assert vacancy.scraped_at is not None


@pytest.mark.asyncio
async def test_create_vacancy_duplicate(db_session):
    """Дубликат по URL должен вернуть None."""
    service = VacancyService(db_session)
    await service.create_vacancy(make_vacancy(1))
    duplicate = await service.create_vacancy(make_vacancy(1))

    assert duplicate is None


@pytest.mark.asyncio
async def test_bulk_create_vacancies(db_session):
    service = VacancyService(db_session)
    vacancies = [make_vacancy(i) for i in range(1, 6)]
    count = await service.bulk_create_vacancies(vacancies)

    assert count == 5


@pytest.mark.asyncio
async def test_bulk_create_skips_duplicates(db_session):
    service = VacancyService(db_session)
    await service.bulk_create_vacancies([make_vacancy(1), make_vacancy(2)])
    # Повторяем #1 и #2, добавляем новую #3
    count = await service.bulk_create_vacancies([make_vacancy(1), make_vacancy(2), make_vacancy(3)])

    assert count == 1


@pytest.mark.asyncio
async def test_get_unanalyzed_vacancies(db_session):
    service = VacancyService(db_session)
    await service.bulk_create_vacancies([make_vacancy(i) for i in range(1, 4)])
    unanalyzed = await service.get_unanalyzed_vacancies()

    assert len(unanalyzed) == 3


@pytest.mark.asyncio
async def test_update_vacancy_ai_data(db_session):
    service = VacancyService(db_session)
    vacancy = await service.create_vacancy(make_vacancy(1))

    ai_data = {"score": 85, "tech_stack": ["FastAPI", "PostgreSQL"], "summary": "Great match."}
    await service.update_vacancy_ai_data(vacancy.id, ai_data)

    unanalyzed = await service.get_unanalyzed_vacancies()
    assert len(unanalyzed) == 0


# ── AIService tests (mocked) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_service_returns_valid_result():
    from app.services.ai_service import AIService

    mock_response = MagicMock()
    mock_response.text = '{"score": 78, "tech_stack": ["Python", "FastAPI"], "summary": "Good fit."}'

    with patch("app.services.ai_service.genai.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        service = AIService(user_skills="Python, FastAPI")
        result = await service.analyze_vacancy("We need a Python developer with FastAPI.")

    assert result is not None
    assert result["score"] == 78
    assert "FastAPI" in result["tech_stack"]


@pytest.mark.asyncio
async def test_ai_service_clamps_score():
    """Score должен быть зажат в 0-100 даже если модель вернула что-то кривое."""
    from app.services.ai_service import AIService

    mock_response = MagicMock()
    mock_response.text = '{"score": 150, "tech_stack": [], "summary": "Weird score."}'

    with patch("app.services.ai_service.genai.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        service = AIService()
        result = await service.analyze_vacancy("Some job.")

    assert result["score"] == 100


# ── API endpoint tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_index_empty(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "JobEngine" in response.text


@pytest.mark.asyncio
async def test_index_shows_vacancies(client, db_session):
    service = VacancyService(db_session)
    await service.bulk_create_vacancies([make_vacancy(i) for i in range(1, 4)])

    response = await client.get("/")
    assert response.status_code == 200
    assert "Python Developer #1" in response.text


@pytest.mark.asyncio
async def test_vacancy_detail(client, db_session):
    service = VacancyService(db_session)
    vacancy = await service.create_vacancy(make_vacancy(1))

    response = await client.get(f"/vacancy/{vacancy.id}")
    assert response.status_code == 200
    assert "Python Developer #1" in response.text


@pytest.mark.asyncio
async def test_vacancy_detail_not_found(client):
    response = await client.get("/vacancy/99999")
    assert response.status_code in (200, 303)  # редирект на /


@pytest.mark.asyncio
async def test_export_csv(client, db_session):
    service = VacancyService(db_session)
    v = await service.create_vacancy(make_vacancy(1))
    await service.update_vacancy_ai_data(v.id, {
        "score": 80, "tech_stack": ["Python"], "summary": "Good."
    })

    response = await client.get("/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Python Developer #1" in response.text


@pytest.mark.asyncio
async def test_clear_database(client, db_session):
    service = VacancyService(db_session)
    await service.bulk_create_vacancies([make_vacancy(i) for i in range(1, 4)])

    response = await client.post("/clear", follow_redirects=True)
    assert response.status_code == 200

    unanalyzed = await service.get_unanalyzed_vacancies()
    assert len(unanalyzed) == 0