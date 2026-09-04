from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: str


@app.get("/api/health")
def health_check():
    return {"message": "FastAPI is connected"}


@app.post("/api/scrape")
def scrape_page(request: ScrapeRequest):
    url = request.url.strip()

    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://"
        )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not scrape URL: {error}"
        )

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    description_tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    description = (
        description_tag.get("content", "").strip()
        if description_tag
        else None
    )

    return {
        "url": url,
        "title": title,
        "description": description,
    }