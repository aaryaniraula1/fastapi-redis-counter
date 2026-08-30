# Scraping API (Async)

FastAPI endpoint that scrapes a webpage's title and description in the 
background, using Redis + RQ for job processing.

## Run it
1. Make sure Docker is installed and running


## Start a scrape job
Send a POST request (target URL must be URL-encoded). This can't be 
done by pasting a link in a browser, since browsers only send GET 
requests. Example using PowerShell:

   Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/scrape/https%3A%2F%2Fexample.com" -Method POST -UseBasicParsing

Returns immediately, no waiting:
   {"task_id": "...", "status": "processing"}

## Check the result
These are GET requests, so they work directly in a browser too.

By task ID:
   http://127.0.0.1:8000/api/result/<task_id>

By URL (no need to remember the task ID):
   http://127.0.0.1:8000/api/result?url=https://example.com

Response while still working:
   {"status": "processing"}

Response once done:
   {"status": "completed", "result": {"url": "...", "title": "...", "description": "..."}}

## Notes
- Results and URL to task mappings are cached in Redis with a 1-hour expiry.
