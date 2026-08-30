FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY forest_crawler/ ./forest_crawler

WORKDIR /app/forest_crawler

CMD ["scrapy", "crawl", "forest", "-o", "/app/output/forest_data.json"]