import sqlite3
import pandas as pd
import json

DB_PATH = "data/jobs.db"

def export_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Read to Pandas DataFrame
    df = pd.read_sql_query("SELECT * FROM scraped_jobs ORDER BY created_at DESC", conn)
    
    # Export to CSV
    df.to_csv("data/scraped_jobs.csv", index=False)
    print("✅ Exported to data/scraped_jobs.csv")
    
    # Export to JSON
    df.to_json("data/scraped_jobs.json", orient="records", indent=2, force_ascii=False)
    print("✅ Exported to data/scraped_jobs.json")
    
    conn.close()

if __name__ == "__main__":
    export_data()