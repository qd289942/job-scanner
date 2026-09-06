#!/bin/bash
set -eo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
PROJECT_DIR="/mnt/c/Users/Kuan/Desktop/Practice/Job_Scanner/job-scanner"
LOG_DIR="${PROJECT_DIR}/logs"
ENV_FILE="${PROJECT_DIR}/.env"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/output_${TIMESTAMP}.log"

cd "$PROJECT_DIR"

{
    echo "========================================================"
    echo "🚀 Job Scanner Pipeline Started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================"

    if [ -f "$ENV_FILE" ]; then
        echo "📄 Loading environment variables from"
        set -a
        # shellcheck disable=SC1090
        source "$ENV_FILE"
        set +a
    else
        echo "⚠️ Warning: .env file not found at ${ENV_FILE}"
    fi
    env

    echo "🔨 Building Docker image..."
    docker build -t job-scanner .
    
    echo "🏃 Running container..."

    if [ -f "$ENV_FILE" ]; then
        docker run --rm -i --env-file "$ENV_FILE" job-scanner python test_api.py
    else
        docker run --rm -i job-scanner python test_api.py
    fi
    
    echo "========================================================"
    echo "✅ Finished Successfully: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================"
} > "$LOG_FILE" 2>&1

find "$LOG_DIR" -type f -name "output_*.log" -mtime +30 -delete