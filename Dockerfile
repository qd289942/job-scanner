FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Debian Bookworm is officially recognized by Playwright
RUN playwright install --with-deps chromium

COPY . .

VOLUME ["/app/data"]

CMD ["python", "main.py"]