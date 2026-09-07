import requests
from bs4 import BeautifulSoup


def scrape_website(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title_tag = soup.find("title")

    title = (
        title_tag.get_text(strip=True)
        if title_tag
        else None
    )

    description_tag = soup.find(
        "meta",
        attrs={"name": "description"},
    )

    description = None

    if description_tag:
        content = description_tag.get("content")
        description = content.strip() if content else None

    return {
        "url": url,
        "title": title,
        "description": description,
    }