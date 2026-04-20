import sys
import asyncio
import uvicorn

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    # Убрали reload=True, чтобы не плодить процессы, и добавили log_level
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, log_level="info")