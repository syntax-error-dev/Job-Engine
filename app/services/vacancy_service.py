from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.vacancy import Vacancy
from app.schemas.vacancy import VacancyCreate


class VacancyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_vacancy(self, vacancy_data: VacancyCreate):
        # Проверяем по URL, чтобы не плодить дубликаты
        existing = await self.db.execute(
            select(Vacancy).where(Vacancy.url == str(vacancy_data.url))
        )
        if existing.scalar_one_or_none():
            return None

        # Превращаем Pydantic-схему в модель SQLAlchemy
        db_vacancy = Vacancy(
            title=vacancy_data.title,
            company=vacancy_data.company,
            url=str(vacancy_data.url),
            description=vacancy_data.description,
            source=vacancy_data.source,
            salary=vacancy_data.salary
        )

        self.db.add(db_vacancy)
        await self.db.commit()
        await self.db.refresh(db_vacancy)
        return db_vacancy

    async def get_unanalyzed_vacancies(self):
        # Берем вакансии, которые еще не проходили через ИИ
        result = await self.db.execute(
            select(Vacancy).where(Vacancy.is_analyzed == False)
        )
        return result.scalars().all()

    async def update_vacancy_ai_data(self, vacancy_id: int, ai_data: dict):
        # Обновляем поля результатами из ИИ
        result = await self.db.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id)
        )
        db_vacancy = result.scalar_one_or_none()
        if db_vacancy:
            db_vacancy.suitability_score = ai_data.get("score")
            db_vacancy.technologies = ai_data.get("tech_stack")
            db_vacancy.ai_summary = ai_data.get("summary")
            db_vacancy.is_analyzed = True
            await self.db.commit()