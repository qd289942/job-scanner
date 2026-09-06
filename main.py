import asyncio
import os
from database import JobDatabase
# from scrapers.greenhouse import GreenhouseScraper
# from scrapers.linkedin import LinkedInGuestScraper
from scrapers.jobs_ch_api import JobsChApiScraper

async def run_pipeline():
    os.makedirs("/app/data", exist_ok=True)
    db = JobDatabase()
    
    print("🚀 [Ingestion Worker] Starting scrape cycle...")

    scrapers = [
        # Target ATS boards
        # GreenhouseScraper(board_token="airbnb", company_name="Airbnb"),
        # GreenhouseScraper(board_token="stripe", company_name="Stripe"),
        JobsChApiScraper(search_term="DevOps", location="Genf", limit=20),
        # Target aggregate searches
        # LinkedInGuestScraper(search_keywords="Platform%20Engineer", location="Germany", limit=10),
    ]

    total_scraped = 0
    total_new = 0

    for scraper in scrapers:
        print(f"\n📡 Executing scraper: {scraper.source_name} ({scraper.target_name})")
        try:
            async for job in scraper.scrape():
                total_scraped += 1
                is_inserted = db.insert_job(job)
                if is_inserted:
                    total_new += 1
                    print(f"  ✨ [NEW] {job.title} @ {job.company} ({job.location})")
                else:
                    print(f"  ⏭️ [DEDUPED] {job.title} @ {job.company}")
        except Exception as e:
            print(f"❌ Scraper failure on {scraper.source_name}: {e}")

    print(f"\n📊 [Scrape Summary] Ingested: {total_scraped} | New unique jobs queued: {total_new}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())