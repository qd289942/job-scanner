import httpx
from bs4 import BeautifulSoup
from typing import AsyncGenerator
from scrapers.base import BaseScraper
from config import RawJobListing, USER_AGENT

class GreenhouseScraper(BaseScraper):
    def __init__(self, board_token: str, company_name: str):
        super().__init__(source_name="greenhouse")
        self.board_token = board_token
        self.company_name = company_name
        self.api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"

    async def scrape(self) -> AsyncGenerator[RawJobListing, None]:
        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(self.api_url)
            if response.status_code != 200:
                print(f"❌ [Greenhouse] Error fetching {self.board_token}: Status {response.status_code}")
                return

            data = response.json()
            jobs = data.get("jobs", [])

            for item in jobs:
                job_id = str(item.get("id"))
                title = item.get("title", "").strip()
                location = item.get("location", {}).get("name", "Unknown")
                url = item.get("absolute_url")
                
                # Greenhouse returns rendered HTML in content; clean to text
                raw_html = item.get("content", "")
                soup = BeautifulSoup(raw_html, "html.parser")
                clean_text = soup.get_text(separator="\n").strip()

                yield RawJobListing(
                    source=self.source_name,
                    external_id=job_id,
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=url,
                    raw_description=clean_text
                )