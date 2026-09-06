from datetime import datetime, timedelta
import os

import httpx
import json
import asyncio
from bs4 import BeautifulSoup
from config import USER_AGENT

# Notion configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = "3d1bff35043f8019a0dce770e092f4ab"
NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_QUERY_URL = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

async def job_exists_in_notion(client: httpx.AsyncClient, job_url: str) -> bool:
    """Check if job already exists in Notion database by URL"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "filter": {
            "property": "URL",
            "url": {
                "equals": job_url
            }
        }
    }
    
    try:
        resp = await client.post(NOTION_QUERY_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            return len(results) > 0
        return False
    except Exception as e:
        print(f"  ⚠️ Error checking Notion: {e}")
        return False

async def add_job_to_notion(client: httpx.AsyncClient, job_data: dict) -> str:
    """
    Add a single job to Notion database.
    Returns:
        "skipped": already exists
        "added": successfully created
        "failed": failed to add
    """
    job_url = job_data.get("url", "")
    if job_url:
        exists = await job_exists_in_notion(client, job_url)
        if exists:
            print(f"  ⏭️ Already exists: {job_data['title'][:50]}")
            return "skipped"
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    properties = {
        "Title": {
            "title": [
                {
                    "text": {
                        "content": job_data["title"][:100]
                    }
                }
            ]
        },
        "Company": {
            "rich_text": [
                {
                    "text": {
                        "content": job_data["company"]
                    }
                }
            ]
        },
        "Location": {
            "rich_text": [
                {
                    "text": {
                        "content": job_data["location"]
                    }
                }
            ]
        },
        "Technologies": {
            "multi_select": [
                {"name": tech} for tech in job_data["technologies"]
            ]
        },
        "URL": {
            "url": job_data["url"]
        },
        "Preview ": {
            "rich_text": [
                {
                    "text": {
                        "content": job_data["preview"][:500]
                    }
                }
            ]
        },
        "Status": {
            "status": {
                "name": "Not started"
            }
        }
    }
    
    posted_date = job_data.get("posted_date", "")
    if posted_date:
        properties["Posted Date"] = {
            "date": {
                "start": posted_date
            }
        }
    
    payload = {
        "parent": {
            "database_id": NOTION_DATABASE_ID
        },
        "properties": properties
    }
    
    try:
        resp = await client.post(NOTION_API_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            print(f"  ✅ Added to Notion: {job_data['title'][:50]}")
            return "added"
        else:
            print(f"  ❌ Notion error: {resp.status_code} - {resp.text}")
            return "failed"
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return "failed"

async def test_jobs_ch_api():
    url = "https://www.jobs.ch/api/v1/public/search"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    }
    
    technologies = [
        "TypeScript", 
        # "JavaScript", 
        # "React", 
        # "Node.js", 
        # "Python", 
        # "Java", 
        # "Docker", 
        # "Kubernetes", 
        # "DevOps", 
        # "PostgreSQL",
        # "CI/CD", 
        # "Git", 
        # "Linux", 
        # "Copilot",
        # "Angular",
        # "Backstage",
        # "Platform Engineering",
        ]
    all_jobs = {}

    # Calculate the cutoff date (45 days ago)
    fourtyfive_days_ago = datetime.now() - timedelta(days=45)

    async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
        print("📋 Checking Notion database properties...")
        await check_notion_database(client)
        print()

        print("\n🔄 Cleaning up 'Not started' jobs...")
        await delete_not_started_jobs(client)
        print()

        for tech in technologies:
            print(f"\n🔍 Searching for: {tech}")
            print("=" * 80)
            
            limit = 50
            results_yielded = 0
            page = 1
            
            while results_yielded < limit:
                params = {
                    "query": tech,
                    "location": "Zürich",
                    "rows": min(20, limit - results_yielded),
                    "sort": "date",
                    "page": page
                }
                
                print(f"  📄 Fetching page {page}...")
                
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    print(f"  ❌ Error: {resp.status_code}")
                    break
                
                data = resp.json()
                documents = data.get("documents", [])
                
                print(f"  ✓ Found {len(documents)} jobs on this page")
                
                if not documents:
                    print(f"  ℹ️ No more results for {tech}")
                    break
                
                for job in documents:
                    if results_yielded >= limit:
                        break
                    
                    job_id = job.get("job_id")

                    title = job.get("title", "").lower()
                    exclude_keywords = ["internship", "intern", "praktikum", "praktikant", "werkstudent", "trainee", "student"]
                    if any(kw in title for kw in exclude_keywords):
                        continue

                    if job_id not in all_jobs:
                        # Extract and parse the publication date
                        pub_date_str  = job.get("publication_date", "")
                        # Convert ISO format to date only: "2026-09-04T07:32:28+02:00" → "2026-09-04"
                        posted_date = ""
                        if pub_date_str:
                            try:
                                dt_parsed = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                                if dt_parsed.replace(tzinfo=None) < fourtyfive_days_ago:
                                    continue
                                posted_date = pub_date_str.split("T")[0]
                            except Exception as e:
                                print(f"  ❌ Error parsing publication date for job {job_id}: {e}")
                                posted_date = ""
                        
                        all_jobs[job_id] = {
                            "title": job.get("title"),
                            "company": job.get("company_name"),
                            "location": job.get("place"),
                            "url": job.get("_links", {}).get("detail_en", {}).get("href"),
                            "preview": job.get("preview"),
                            "technologies": [tech],
                            "posted_date": posted_date  # Will be empty string if not available
                        }
                        results_yielded += 1
                    else:
                        if tech not in all_jobs[job_id]["technologies"]:
                            all_jobs[job_id]["technologies"].append(tech)
                
                current_page = data.get("current_page", 1)
                num_pages = data.get("num_pages", 1)
                
                if current_page >= num_pages or results_yielded >= limit:
                    break
                
                page += 1
        
        # Upload all jobs to Notion
        print(f"\n\n📤 Uploading to Notion...")
        print("=" * 80)
        
        added_count = 0
        skipped_count = 0
        failed_count = 0
        for job_id, job_data in all_jobs.items():
            status = await add_job_to_notion(client, job_data)
            if status == "added":
                added_count += 1
            elif status == "skipped":
                skipped_count += 1
            else:
                failed_count += 1
    
        # Display summary
        print(f"\n\n📊 SUMMARY")
        print("=" * 80)
        print(f"Total unique jobs found: {len(all_jobs)}")
        print(f"✅ Newly added to Notion: {added_count}")
        print(f"⏭️ Already existed: {skipped_count}")
        if failed_count > 0:
            print(f"❌ Failed to add: {failed_count}")


async def check_notion_database(client: httpx.AsyncClient):
    """Check what properties exist in the Notion database with detailed info"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28"
    }
    
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    
    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            properties = data.get("properties", {})
            print("\n📋 Database Properties (DETAILED):")
            print("=" * 80)
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get("type")
                # Print with quotes to see exact spacing
                print(f"  Name: '{prop_name}'")
                print(f"  Type: {prop_type}")
                print(f"  ID: {prop_info.get('id', 'N/A')}")
                print()
            return properties
        else:
            print(f"Error: {resp.status_code}")
            return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}

async def delete_not_started_jobs(client: httpx.AsyncClient):
    """Delete all jobs marked as 'Not started' from Notion with pagination support"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    deleted_count = 0
    has_more = True
    start_cursor = None
    
    try:
        while has_more:
            payload = {
                "filter": {
                    "property": "Status",
                    "status": {
                        "equals": "Not started"
                    }
                },
                "page_size": 100 
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            resp = await client.post(NOTION_QUERY_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"❌ Error querying Notion: {resp.status_code} - {resp.text}")
                break
                
            data = resp.json()
            results = data.get("results", [])
            
            for page in results:
                page_id = page.get("id")
                delete_url = f"https://api.notion.com/v1/pages/{page_id}"
                
                delete_resp = await client.patch(delete_url, headers=headers, json={"archived": True})
                if delete_resp.status_code == 200:
                    deleted_count += 1
                elif delete_resp.status_code == 429:
                    await asyncio.sleep(0.5)
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
            
        print(f"🗑️  Deleted total {deleted_count} 'Not started' jobs from Notion")
        return deleted_count
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return deleted_count

if __name__ == "__main__":
    asyncio.run(test_jobs_ch_api())