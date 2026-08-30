# Scraping API (Async)

FastAPI endpoint that scrapes a webpage's title and description in the background, using Redis + RQ for job processing.


## Start a scrape job 
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/scrape/https%3A%2F%2Fexample.com" -Method POST -UseBasicParsing

Returns immediately:
{"task_id": "...", "status": "processing"}

## Check result by task ID
http://127.0.0.1:8000/api/result/<task_id>

## Check result by URL
http://127.0.0.1:8000/api/result?url=https://example.com