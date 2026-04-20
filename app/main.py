import asyncio
import csv
import io
import json
import logging
from typing import List, Optional

from fastapi import FastAPI, Depends, Request, Form, Query, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from sqlalchemy import delete, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db, async_session
from app.models.vacancy import Vacancy

from test_parser import run_all_scrapers
from analyze_jobs import start_analysis

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart JobEngine Admin")
templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 20


# --- Фоновая задача для пайплайна ---
async def run_pipeline_task(keyword: str, experience: str, skills: str, sources: List[str]):
    logger.info(f"🤖 === STARTING PIPELINE: {keyword} ===")
    try:
        # 1. Запускаем скраперы
        await run_all_scrapers(
            keyword=keyword,
            exp=experience,
            selected_sources=sources
        )
        # 2. Запускаем анализ
        await start_analysis(user_skills=skills)
        logger.info("✅ PIPELINE FINISHED SUCCESSFULLY.")
    except Exception as e:
        # Теперь, если ИИ упадет, мы УВИДИМ это в консоли
        logger.error(f"❌ PIPELINE FAILED: {e}", exc_info=True)


@app.get("/")
async def index(
        request: Request,
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        source: Optional[str] = Query(None),
        min_score: Optional[str] = Query(None),
        sort: str = Query("score_desc"),
):
    min_score_int: Optional[int] = None
    if min_score and min_score.strip().isdigit():
        min_score_int = int(min_score)
    query = select(Vacancy)

    if source:
        query = query.where(Vacancy.source == source)
    if min_score_int is not None:
        query = query.where(Vacancy.suitability_score >= min_score_int)

    sort_map = {
        "score_desc": desc(Vacancy.suitability_score),
        "score_asc": asc(Vacancy.suitability_score),
        "title_asc": asc(Vacancy.title),
        "company_asc": asc(Vacancy.company),
    }
    order = sort_map.get(sort, desc(Vacancy.suitability_score))
    query = query.order_by(order)

    count_result = await db.execute(query)
    all_jobs = count_result.scalars().all()
    total = len(all_jobs)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    offset = (page - 1) * PAGE_SIZE
    paged_jobs = all_jobs[offset: offset + PAGE_SIZE]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "jobs": paged_jobs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "source": source or "",
        "min_score": min_score_int if min_score_int is not None else "",
        "sort": sort,
    })


@app.get("/api/stream")
async def stream_vacancies(request: Request):
    """SSE endpoint."""

    async def event_generator():
        seen_ids = {}
        idle_ticks = 0

        while True:
            if await request.is_disconnected():
                break

            try:
                async with async_session() as session:
                    result = await session.execute(
                        select(Vacancy).order_by(desc(Vacancy.suitability_score))
                    )
                    jobs = result.scalars().all()

                changed = False
                for job in jobs:
                    prev = seen_ids.get(job.id)
                    curr = (job.suitability_score, job.is_analyzed)

                    if prev != curr:
                        seen_ids[job.id] = curr
                        changed = True

                        payload = json.dumps({
                            "id": job.id,
                            "title": job.title,
                            "company": job.company,
                            "source": job.source,
                            "salary": job.salary,
                            "score": job.suitability_score,
                            "is_analyzed": job.is_analyzed,
                            "ai_summary": job.ai_summary or "",
                            "technologies": job.technologies or [],
                        }, ensure_ascii=False)

                        yield f"data: {payload}\n\n"

                if changed:
                    idle_ticks = 0
                else:
                    idle_ticks += 1

                if idle_ticks >= 20:
                    yield "event: done\ndata: done\n\n"
                    break

            except Exception as e:
                logger.error(f"SSE Error: {e}")

            # Увеличил задержку, чтобы база успевала "дышать" и записывать данные от ИИ
            await asyncio.sleep(2.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/vacancy/{vacancy_id}")
async def vacancy_detail(vacancy_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
    job = result.scalar_one_or_none()
    if not job:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("detail.html", {"request": request, "job": job})


@app.get("/export/csv")
async def export_csv(
        db: AsyncSession = Depends(get_db),
        source: Optional[str] = Query(None),
        min_score: Optional[str] = Query(None),
):
    min_score_int: Optional[int] = None
    if min_score and min_score.strip().isdigit():
        min_score_int = int(min_score)

    query = select(Vacancy).order_by(desc(Vacancy.suitability_score))
    if source:
        query = query.where(Vacancy.source == source)
    if min_score_int is not None:
        query = query.where(Vacancy.suitability_score >= min_score_int)

    result = await db.execute(query)
    jobs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Company", "Source", "Score", "Salary", "Technologies", "AI Summary", "URL"])
    for job in jobs:
        writer.writerow([
            job.id, job.title, job.company, job.source,
            job.suitability_score, job.salary or "",
            ", ".join(job.technologies or []),
                                   job.ai_summary or "", job.url,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vacancies.csv"}
    )


# --- ИЗМЕНЕНИЯ ЗДЕСЬ: Используем BackgroundTasks вместо subprocess ---
@app.post("/run")
async def run_pipeline(
        background_tasks: BackgroundTasks,
        keyword: str = Form(...),
        experience: str = Form(...),
        skills: str = Form(""),
        sources: List[str] = Form(["djinni", "dou", "linkedin"])
):
    # Добавляем задачу в фон. FastAPI сам запустит её и не заблокирует ответ
    background_tasks.add_task(run_pipeline_task, keyword, experience, skills, sources)
    return RedirectResponse(url="/?stream=1", status_code=303)


@app.post("/clear")
async def clear_database(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Vacancy))
    await db.commit()
    return RedirectResponse(url="/", status_code=303)