from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from redis.exceptions import RedisError
from rq import Retry
from rq.exceptions import NoSuchJobError
from rq.job import Job

from api.queue import redis_connection, scrape_queue
from api.tasks import scrape_website


app = FastAPI(
    title="Web Scraper API"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: HttpUrl


@app.get("/api/health")
def health_check():
    try:
        redis_connection.ping()

    except RedisError as error:
        raise HTTPException(
            status_code=503,
            detail="Redis is unavailable",
        ) from error

    return {
        "message": "FastAPI and Redis are connected"
    }


@app.post(
    "/api/scrape",
    status_code=status.HTTP_202_ACCEPTED,
)
def create_scrape_job(request: ScrapeRequest):
    url = str(request.url)

    job_id = f"UI-{uuid4().hex[:9]}"

    try:
        job = scrape_queue.enqueue(
            scrape_website,
            url,
            job_id=job_id,
            job_timeout=30,
            result_ttl=600,
            failure_ttl=600,
            retry=Retry(max=2),
        )

    except RedisError as error:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to the job queue",
        ) from error

    return {
        "job_id": job.id,
        "status": "queued",
    }


@app.get("/api/jobs/{job_id}")
def get_scrape_job(job_id: str):
    try:
        job = Job.fetch(
            job_id,
            connection=redis_connection,
        )

        job_status = job.get_status(
            refresh=True
        )

    except NoSuchJobError as error:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        ) from error

    except RedisError as error:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to the job queue",
        ) from error

    status_value = (
        job_status.value
        if hasattr(job_status, "value")
        else str(job_status)
    )

    response = {
        "job_id": job.id,
        "status": status_value,
    }

    if status_value == "finished":
        response["result"] = job.result

    elif status_value == "failed":
        response["error"] = "Scraping job failed"

    return response