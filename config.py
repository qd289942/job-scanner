import os
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/jobs.db")
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

class RawJobListing(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    raw_description: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)