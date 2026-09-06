import httpx
from typing import AsyncGenerator
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from config import RawJobListing, USER_AGENT

class JobsChApiScraper(BaseScraper):
    def __init__(self, search_term: str, location: str = "", limit: int = 20, lang: str = "en"):
        super().__init__(source_name="jobsch")
        self.search_term = search_term
        self.location = location
        self.limit = limit
        self.lang = lang
        self.api_url = "https://www.jobs.ch/api/v1/public/search"

    async def scrape(self) -> AsyncGenerator[RawJobListing, None]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": f"{self.lang}-US,{self.lang};q=0.9,de;q=0.8",
        }
        params = {
            "query": self.search_term,
            "location": self.location,
            "rows": min(self.limit, 50),
            "sort": "date"
        }

        # Set verify=False to bypass local issuer certificate verification
        async with httpx.AsyncClient(timeout=20.0, headers=headers, verify=False) as client:
            resp = await client.get(self.api_url, params=params)
            if resp.status_code != 200:
                print(f"❌ [jobs.ch API] HTTP {resp.status_code}: {resp.text[:200]}")
                return

            data = resp.json()
            documents = data.get("documents", [])

            for item in documents[:self.limit]:
                job_id = str(item.get("job_id") or item.get("id"))
                title = item.get("title", "").strip()
                company = item.get("company_name", "Confidential")
                place = item.get("place", "Switzerland")
                
                url = f"https://www.jobs.ch/{self.lang}/vacancies/detail/{job_id}/"
                raw_html = item.get("description", "") or item.get("preview", "")
                
                soup = BeautifulSoup(raw_html, "html.parser")
                clean_text = soup.get_text(separator="\n").strip()
                if not clean_text:
                    clean_text = f"{title} at {company} in {place}"

                yield RawJobListing(
                    source=self.source_name,
                    external_id=job_id,
                    title=title,
                    company=company,
                    location=place,
                    url=url,
                    raw_description=clean_text
                )