# Web Scraper UI

A React + Vite web scraper connected to a FastAPI backend and using Redis Queue (RQ) for background scraping jobs.

## Tech Stack

* React
* Vite
* FastAPI
* Python
* Redis
* RQ
* Requests
* BeautifulSoup
* Docker
* Docker Compose
* Pytest

## Setup and Run

### 1. Install Backend Dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Run the Application

Make sure Docker Desktop is running:

```bash
docker compose up --build
```

FastAPI runs at:

```text
http://127.0.0.1:8000
```

Frontend runs at:

```text
http://localhost:5173
```

### 3. Scrape a Website

Enter a website URL in the empty field and click **Scrape**.

FastAPI queues the scraping job using RQ, the worker processes it in the background, and the frontend displays the job status and scraped result.

## API

Create a scraping job:

```text
POST /api/scrape
```

Check job status:

```text
GET /api/jobs/{job_id}
```

Possible statuses:

```text
queued
started
finished
failed
```

