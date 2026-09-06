import asyncio
from typing import AsyncGenerator
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from config import RawJobListing, HEADLESS_BROWSER, USER_AGENT

class LinkedInGuestScraper(BaseScraper):
    def __init__(self, search_keywords: str, location: str, limit: int = 15):
        super().__init__(source_name="linkedin")
        self.search_keywords = search_keywords
        self.location = location
        self.limit = limit
        self.search_url = (
            f"https://www.linkedin.com/jobs/search?keywords={search_keywords}"
            f"&location={location}&sortBy=DD"
        )

    async def scrape(self) -> AsyncGenerator[RawJobListing, None]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS_BROWSER)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            try:
                print(f"🔍 [LinkedIn] Navigating to: {self.search_url}")
                await page.goto(self.search_url, wait_until="domcontentloaded", timeout=30000)

                # Dismiss cookie banner if present
                try:
                    cookie_btn = page.locator('button[data-tracking-control-name="ga-cookie-banner-accept"]')
                    if await cookie_btn.is_visible(timeout=3000):
                        await cookie_btn.click()
                except Exception:
                    pass

                # Scroll down to load initial cards
                for _ in range(3):
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(1)

                job_cards = await page.locator("ul.jobs-search__results-list > li").all()
                count = 0

                for card in job_cards:
                    if count >= self.limit:
                        break

                    try:
                        link_elem = card.locator("a.base-card__full-link")
                        if not await link_elem.count():
                            continue

                        job_url = await link_elem.get_attribute("href")
                        # Strip query tracking parameters
                        job_url = job_url.split("?")[0] if job_url else ""
                        
                        # Extract LinkedIn URN Job ID from URL or attributes
                        job_id = job_url.rstrip("/").split("-")[-1]

                        title = (await card.locator("h3.base-search-card__title").inner_text()).strip()
                        company = (await card.locator("h4.base-search-card__subtitle").inner_text()).strip()
                        location = (await card.locator("span.job-search-card__location").inner_text()).strip()

                        # Click card to render full JD panel
                        await card.click()
                        await asyncio.sleep(1.2)

                        jd_container = page.locator(".show-more-less-html__markup")
                        raw_desc = ""
                        if await jd_container.count():
                            raw_html = await jd_container.inner_html()
                            soup = BeautifulSoup(raw_html, "html.parser")
                            raw_desc = soup.get_text(separator="\n").strip()

                        if not raw_desc:
                            raw_desc = f"{title} at {company}"

                        count += 1
                        yield RawJobListing(
                            source=self.source_name,
                            external_id=job_id,
                            title=title,
                            company=company,
                            location=location,
                            url=job_url,
                            raw_description=raw_desc
                        )

                    except Exception as item_err:
                        print(f"⚠️ [LinkedIn] Failed parsing individual card: {item_err}")
                        continue

            finally:
                await context.close()
                await browser.close()