import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "output" / "hierarchy.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Forest Government Research)"
}

TIMEOUT = 10

SITES = [
    {
        "domain": "dofsc.gov.np",
        "name": "Department of Forests and Soil Conservation",
        "parent": "Ministry of Forests and Environment",
        "parent_np": "वन तथा वातावरण मन्त्रालय",
    },
    {
        "domain": "dnpwc.gov.np",
        "name": "Department of National Parks and Wildlife Conservation",
        "parent": "Ministry of Forests and Environment",
        "parent_np": "वन तथा वातावरण मन्त्रालय",
    },
    {
        "domain": "frtc.gov.np",
        "name": "Forest Research and Training Centre",
        "parent": "Ministry of Forests and Environment",
        "parent_np": "वन तथा वातावरण मन्त्रालय",
    },
    {
        "domain": "fpdb.gov.np",
        "name": "Forest Product Development Committee",
        "parent": "Ministry of Forests and Environment",
        "parent_np": "वन तथा वातावरण मन्त्रालय",
    },
]


def fetch_page(domain):
    urls = [
        f"https://{domain}/",
        f"http://{domain}/",
    ]

    for url in urls:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
                verify=False
            )

            if response.status_code == 200:
                return response.url, response.text

        except requests.RequestException as error:
            print(f"Could not fetch {url}: {error}")

    return None, None


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_page_info(html):
    soup = BeautifulSoup(html, "html.parser")

    title = None

    if soup.title:
        title = clean_text(soup.title.get_text(" "))

    text = clean_text(soup.get_text(" "))

    return title, text


def find_parent_evidence(text, parent, parent_np=None):
    """
    Checks for the parent org name in either English or
    Nepali, since most of these government sites are
    Nepali-language and only ever use the Nepali form.
    """

    text_lower = text.lower()

    candidates = [parent]

    if parent_np:
        candidates.append(parent_np)

    for candidate in candidates:
        index = text_lower.find(candidate.lower())

        if index != -1:
            start = max(0, index - 250)
            end = min(len(text), index + len(candidate) + 250)
            return text[start:end]

    return None


def process_site(site):
    print(f"\nProcessing: {site['domain']}")

    url, html = fetch_page(site["domain"])

    if not html:
        return {
            "domain": site["domain"],
            "name": site["name"],
            "parent": site["parent"],
            "verified_url": None,
            "page_title": None,
            "parent_evidence": None,
            "status": "fetch_failed",
        }

    title, text = extract_page_info(html)

    evidence = find_parent_evidence(
        text,
        site["parent"],
        site.get("parent_np"),
    )

    status = "verified" if evidence else "parent_not_found_on_homepage"

    print(f"Organisation: {site['name']}")
    print(f"Parent: {site['parent']}")
    print(f"Status: {status}")

    return {
        "domain": site["domain"],
        "name": site["name"],
        "parent": site["parent"],
        "verified_url": url,
        "page_title": title,
        "parent_evidence": evidence,
        "status": status,
    }


def main():
    results = []

    for site in SITES:
        result = process_site(site)
        results.append(result)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\n--------------------------------")
    print(f"Created: {OUTPUT_FILE}")
    print(f"Sites processed: {len(results)}")
    print("--------------------------------")


if __name__ == "__main__":
    main()