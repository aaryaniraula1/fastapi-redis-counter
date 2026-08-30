from fastapi import FastAPI, HTTPException
import redis
from rq import Queue
from rq.job import Job
from app.worker import process_url

app = FastAPI()

cache = redis.Redis(host="redis", port=6379, decode_responses=True)
queue_conn = redis.Redis(host="redis", port=6379)
queue = Queue(connection=queue_conn)


@app.post("/api/scrape/{url:path}")
def start_scrape(url: str):
    existing_task_id = cache.get(f"url_task:{url}")

    if existing_task_id:
        return {"task_id": existing_task_id, "status": "already_processing_or_done"}

    job = queue.enqueue(process_url, url)
    cache.setex(f"url_task:{url}", 3600, job.id)

    return {"task_id": job.id, "status": "processing"}


@app.get("/api/result/{task_id}")
def get_result_by_task_id(task_id: str):
    try:
        job = Job.fetch(task_id, connection=queue_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Task not found")

    if job.is_finished:
        return {"status": "completed", "result": job.result}
    elif job.is_failed:
        return {"status": "failed"}
    else:
        return {"status": "processing"}


@app.get("/api/result")
def get_result_by_url(url: str):
    task_id = cache.get(f"url_task:{url}")

    if not task_id:
        raise HTTPException(status_code=404, detail="No task found for this URL")

    job = Job.fetch(task_id, connection=queue_conn)

    if job.is_finished:
        return {"status": "completed", "result": job.result}
    elif job.is_failed:
        return {"status": "failed"}
    else:
        return {"status": "processing"}