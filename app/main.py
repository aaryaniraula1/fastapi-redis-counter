from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup
import redis
import json

app = FastAPI()

cache = redis.Redis(host="redis", port=6379, decode_responses=True)


@app.get("/api/scrape/{url:path}")
def scrape(url: str):
    cached_result = cache.get(url)

    if cached_result:
        print("CACHE HIT")
        return json.loads(cached_result)

    print("CACHE MISS")

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {e}")

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else None

    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag["content"].strip() if description_tag else None

    result = {
        "url": url,
        "title": title,
        "description": description
    }

    cache.setex(url, 300, json.dumps(result))

    return result