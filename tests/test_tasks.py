from unittest.mock import Mock, patch

import pytest
import requests

from api.tasks import scrape_website


def test_scrape_website_success():
    with patch("api.tasks.requests.get") as mock_get:
        mock_response = Mock()

        mock_response.text = """
        <html>
            <head>
                <title>Test Title</title>
                <meta
                    name="description"
                    content="Test Description"
                >
            </head>
        </html>
        """

        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = scrape_website(
            "https://example.com"
        )

        assert result == {
            "url": "https://example.com",
            "title": "Test Title",
            "description": "Test Description",
        }


def test_scrape_website_without_title():
    with patch("api.tasks.requests.get") as mock_get:
        mock_response = Mock()

        mock_response.text = """
        <html>
            <head>
                <meta
                    name="description"
                    content="Test Description"
                >
            </head>
        </html>
        """

        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = scrape_website(
            "https://example.com"
        )

        assert result["title"] is None
        assert (
            result["description"]
            == "Test Description"
        )


def test_scrape_website_without_description():
    with patch("api.tasks.requests.get") as mock_get:
        mock_response = Mock()

        mock_response.text = """
        <html>
            <head>
                <title>Test Title</title>
            </head>
        </html>
        """

        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = scrape_website(
            "https://example.com"
        )

        assert result["title"] == "Test Title"
        assert result["description"] is None


def test_scrape_website_http_error():
    with patch("api.tasks.requests.get") as mock_get:
        mock_response = Mock()

        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(
                "404 Not Found"
            )
        )

        mock_get.return_value = mock_response

        with pytest.raises(
            requests.exceptions.HTTPError
        ):
            scrape_website(
                "https://example.com"
            )


def test_scrape_website_timeout():
    with patch("api.tasks.requests.get") as mock_get:
        mock_get.side_effect = (
            requests.exceptions.Timeout(
                "Request timed out"
            )
        )

        with pytest.raises(
            requests.exceptions.Timeout
        ):
            scrape_website(
                "https://example.com"
            )