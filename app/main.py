from fastapi import FastAPI, Request, Response
import os
import redis
import uuid

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

@app.get("/")
def hello(request: Request, response: Response):
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie("user_id", user_id)

    count = r.incr(f"user:{user_id}")

    return {"message": "Hello World", "visits": count}