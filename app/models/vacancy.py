from sqlalchemy import String, Text, Integer, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.schemas.enums import JobSource


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    salary: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default=JobSource.DJINNI)

    # Поля для нашего ИИ-функционала
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    suitability_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)