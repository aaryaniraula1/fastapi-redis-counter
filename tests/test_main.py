import json
import requests
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_scraping_success():
    fake_html = """
    <html>
        <head>
            <title>Test Website</title>
            <meta name="description" content="This is a test website">
        </head>
    </html>
    """

    fake_response = Mock()
    fake_response.text = fake_html
    fake_response.raise_for_status.return_value = None

    with patch("app.main.cache.get", return_value=None), \
         patch("app.main.requests.get", return_value=fake_response), \
         patch("app.main.cache.setex") as mock_setex:

        response = client.get("/api/scrape/https%3A%2F%2Fexample.com")

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "Test Website"
    assert data["description"] == "This is a test website"

    mock_setex.assert_called_once()


def test_cache_hit():
    cached_data = {
        "url": "https://example.com",
        "title": "Cached Title",
        "description": "Cached Description"
    }

    with patch(
        "app.main.cache.get",
        return_value=json.dumps(cached_data)
    ), patch("app.main.requests.get") as mock_requests:

        response = client.get("/api/scrape/https%3A%2F%2Fexample.com")

    assert response.status_code == 200
    assert response.json() == cached_data

    mock_requests.assert_not_called()


def test_cache_miss():
    fake_html = """
    <html>
        <head>
            <title>Fresh Website</title>
            <meta name="description" content="Fresh Description">
        </head>
    </html>
    """

    fake_response = Mock()
    fake_response.text = fake_html
    fake_response.raise_for_status.return_value = None

    with patch("app.main.cache.get", return_value=None), \
         patch("app.main.requests.get", return_value=fake_response), \
         patch("app.main.cache.setex") as mock_setex:

        response = client.get("/api/scrape/https%3A%2F%2Fexample.com")

    assert response.status_code == 200
    assert response.json()["title"] == "Fresh Website"

    mock_setex.assert_called_once()


def test_invalid_url():
    with patch(
        "app.main.cache.get",
        return_value=None
    ), patch(
        "app.main.requests.get",
        side_effect=requests.exceptions.RequestException("Invalid URL")
    ):

        response = client.get("/api/scrape/not-a-valid-url")

    assert response.status_code == 400