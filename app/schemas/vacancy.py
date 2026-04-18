from pydantic import BaseModel, HttpUrl, Field
from app.schemas.enums import JobSource


class VacancyBase(BaseModel):
    title: str
    company: str
    salary: str | None = None
    description: str
    url: HttpUrl
    source: JobSource


class VacancyCreate(VacancyBase):
    # Эти поля заполнит ИИ позже, поэтому ставим None по умолчанию
    technologies: list[str] = Field(default_factory=list)
    ai_summary: str | None = None
    suitability_score: int | None = Field(None, ge=0, le=100)


class VacancyResponse(VacancyBase):
    id: int  # Или UUID
    is_analyzed: bool

    class Config:
        from_attributes = True  # Позволяет Pydantic читать данные из моделей SQLAlchemy