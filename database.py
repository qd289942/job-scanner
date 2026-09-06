import sqlite3
import hashlib
from typing import Optional
from config import DATABASE_PATH, RawJobListing

class JobDatabase:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scraped_jobs (
                    hash_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    url TEXT NOT NULL,
                    raw_description TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING_LLM',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON scraped_jobs(status);")
            conn.commit()

    @staticmethod
    def generate_hash(source: str, title: str, company: str, location: str) -> str:
        """
        Generates a normalized fingerprint across core job attributes
        to prevent identical jobs under different external IDs.
        """
        normalized_str = (
            f"{source.strip().lower()}::"
            f"{title.strip().lower()}::"
            f"{company.strip().lower()}::"
            f"{location.strip().lower()}"
        )
        return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()

    def exists(self, hash_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM scraped_jobs WHERE hash_id = ?", (hash_id,))
            return cursor.fetchone() is not None

    def insert_job(self, job: RawJobListing) -> bool:
        """Inserts job if not already processed."""
        # Use composite semantic hash instead of external_id alone
        hash_id = self.generate_hash(job.source, job.title, job.company, job.location)
        
        if self.exists(hash_id):
            return False

        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO scraped_jobs (
                        hash_id, source, external_id, title, company, 
                        location, url, raw_description, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_LLM')
                """, (
                    hash_id, job.source, job.external_id, job.title,
                    job.company, job.location, job.url, job.raw_description
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO scraped_jobs (
                        hash_id, source, external_id, title, company, 
                        location, url, raw_description, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_LLM')
                """, (
                    hash_id, job.source, job.external_id, job.title,
                    job.company, job.location, job.url, job.raw_description
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def fetch_pending_jobs(self, limit: int = 50) -> list[sqlite3.Row]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM scraped_jobs WHERE status = 'PENDING_LLM' LIMIT ?", (limit,)
            )
            return cursor.fetchall()