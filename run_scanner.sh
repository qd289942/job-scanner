#!/bin/bash
set -eo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
PROJECT_DIR="/mnt/c/Users/Kuan/Desktop/Practice/Job_Scanner/job-scanner"
LOG_DIR="${PROJECT_DIR}/logs"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/output_${TIMESTAMP}.log"

cd "$PROJECT_DIR"

{
    echo "========================================================"
    echo "🚀 Job Scanner Pipeline Started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================"

    export NOTION_API_KEY="your_new_notion_token"
    
    echo "🔨 Building Docker image..."
    docker build -t job-scanner .
    
    echo "🏃 Running container..."
    docker run --rm -i -e NOTION_API_KEY="$NOTION_API_KEY" job-scanner python test_api.py
    
    echo "========================================================"
    echo "✅ Finished Successfully: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================"
} > "$LOG_FILE" 2>&1

find "$LOG_DIR" -type f -name "output_*.log" -mtime +30 -delete