from abc import abstractmethod, ABC

import playwright
from playwright.async_api import async_playwright


class BaseParser(ABC):
    @abstractmethod
    async def scrape(self) -> list:
        pass

    async def get_page_content(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(url)
            pass