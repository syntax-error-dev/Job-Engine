import subprocess
from typing import List
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.vacancy import Vacancy

app = FastAPI(title="Smart JobEngine Admin")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Vacancy).order_by(Vacancy.suitability_score.desc())
    )
    jobs = result.scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "jobs": jobs})

@app.post("/run")
async def run_pipeline(
        keyword: str = Form(...),
        experience: str = Form(...),
        skills: str = Form(""),
        sources: List[str] = Form(["djinni", "dou", "linkedin"])
):
    sources_str = ",".join(sources)

    subprocess.Popen([
        sys.executable, "main_pipeline.py",
        "--keyword", keyword,
        "--exp", experience,
        "--skills", skills,
        "--sources", sources_str
    ])

    return RedirectResponse(url="/", status_code=303)


@app.post("/clear")
async def clear_database(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Vacancy))
    await db.commit()
    return RedirectResponse(url="/", status_code=303)