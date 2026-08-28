# Scraping API

FastAPI endpoint that scrapes a webpage's title and description.

## Run it
1. Make sure Docker is installed and running
2. docker compose up --build
3. Go to (target URL must be URL-encoded):
   http://127.0.0.1:8000/api/scrape/https%3A%2F%2Fexample.com

## Try a different website
Replace the encoded URL at the end with any site wanted, for example:
   http://127.0.0.1:8000/api/scrape/https%3A%2F%2Fwww.google.com
