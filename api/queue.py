import os

from redis import Redis
from rq import Queue


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://redis:6379/0",
)

redis_connection = Redis.from_url(REDIS_URL)

scrape_queue = Queue(
    "scraping",
    connection=redis_connection,
    default_timeout=30,
)