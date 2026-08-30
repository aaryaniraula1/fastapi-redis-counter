import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class ForestSpider(scrapy.Spider):
    name = "forest"

    allowed_domains = [
        "mofe.gov.np",
        "moald.gov.np",
        "dofsc.gov.np",
        "dnpwc.gov.np",
        "frtc.gov.np",
        "redd.gov.np",
    ]

    start_urls = [
        "https://mofe.gov.np",
        "https://moald.gov.np",
        "https://dofsc.gov.np",
        "https://dnpwc.gov.np/en/",
        "https://frtc.gov.np",
        "https://redd.gov.np/",
    ]

    relevant_keywords = [
        "organizational structure",
        "organization structure",
        "organogram",
        "organization",
        "department",
        "office",
        "section",
        "function",
        "report",
        "act",
        "regulation",
        "forest",
        "division",
    ]

    def parse(self, response):
        content_type = response.headers.get("Content-Type", b"").decode("utf-8", errors="ignore")
        if "text/html" not in content_type:
            return

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(" ", strip=True) if soup.title else ""

        headings = []
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = heading.get_text(" ", strip=True)
            if text:
                headings.append(text)

        page_text = soup.get_text(" ", strip=True)

        text_to_check = (
            title + " " +
            " ".join(headings) + " " +
            page_text[:10000]
        ).lower()

        relevant = any(
            keyword in text_to_check
            for keyword in self.relevant_keywords
        )

        if relevant:
            yield {
                "url": response.url,
                "domain": urlparse(response.url).netloc,
                "title": title,
                "headings": headings,
                "content": page_text[:5000],
            }

        for link in response.css("a::attr(href)").getall():
            next_url = response.urljoin(link)
            parsed = urlparse(next_url)

            if parsed.scheme in ["http", "https"]:
                yield response.follow(next_url, callback=self.parse)