from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.vacancy import Vacancy
from app.schemas.vacancy import VacancyCreate

class VacancyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_vacancy(self, vacancy_data: VacancyCreate):
        existing = await self.db.execute(
            select(Vacancy).where(Vacancy.url == str(vacancy_data.url))
        )
        if existing.scalar_one_or_none():
            return None

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

    async def bulk_create_vacancies(self, vacancies: list[VacancyCreate]) -> int:
        if not vacancies:
            return 0

        urls = [str(v.url) for v in vacancies]
        existing_urls_result = await self.db.execute(
            select(Vacancy.url).where(Vacancy.url.in_(urls))
        )
        existing_urls = set(existing_urls_result.scalars().all())

        new_vacancies = [
            Vacancy(
                title=v.title,
                company=v.company,
                url=str(v.url),
                description=v.description,
                source=v.source,
                salary=v.salary
            )
            for v in vacancies if str(v.url) not in existing_urls
        ]

        if new_vacancies:
            self.db.add_all(new_vacancies)
            await self.db.commit()
            return len(new_vacancies)
        return 0

    async def get_unanalyzed_vacancies(self):
        result = await self.db.execute(
            select(Vacancy).where(Vacancy.is_analyzed == False)
        )
        return result.scalars().all()

    async def update_vacancy_ai_data(self, vacancy_id: int, ai_data: dict):
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