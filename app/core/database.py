from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Для начала будем использовать SQLite (файл jobs.db).
# Когда будешь готов к Docker и Postgres — просто поменяем строку подключения.
DATABASE_URL = "sqlite+aiosqlite:///./jobs.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# Зависимость для FastAPI, чтобы получать сессию БД в роутах
async def get_db():
    async with async_session() as session:
        yield session