import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def fetch_page(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            verify=False
        )

        if response.status_code == 200:
            return response

    except requests.RequestException as error:
        print(f"Could not fetch {url}: {error}")

    return None


def fetch_homepage(domain):
    for url in (
        f"https://{domain}/",
        f"http://{domain}/"
    ):
        response = fetch_page(url)

        if response:
            return response

    return None


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(response):
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return clean_text(soup.get_text(" "))


def get_relevant_links(response):
    soup = BeautifulSoup(response.text, "html.parser")

    keywords = [
        "about",
        "introduction",
        "organization",
        "organisation",
        "structure",
        "chart",
        "profile",
        "ministry",
        "background",
        "overview",
    ]

    base_url = response.url
    base_domain = urlparse(base_url).netloc

    links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        link_text = link.get_text(" ", strip=True).lower()

        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        # Only follow links belonging to the same government website
        if parsed_url.netloc != base_domain:
            continue

        searchable_text = (
            f"{link_text} {parsed_url.path.lower()}"
        )

        if any(
            keyword in searchable_text
            for keyword in keywords
        ):
            if full_url not in links:
                links.append(full_url)

    return links[:8]


def find_parent_evidence(text, parent, parent_np):
    candidates = [
        parent,
        parent_np
    ]

    text_lower = text.lower()

    for candidate in candidates:
        index = text_lower.find(candidate.lower())

        if index != -1:
            start = max(0, index - 300)
            end = min(
                len(text),
                index + len(candidate) + 300
            )

            return text[start:end]

    return None


def process_site(site):
    domain = site["domain"]
    name = site["name"]
    parent = site["parent"]
    parent_np = site.get("parent_np")

    print(f"\nProcessing: {domain}")

    homepage = fetch_homepage(domain)

    if not homepage:
        print("Homepage could not be accessed.")

        return {
            "domain": domain,
            "name": name,
            "parent": parent,
            "verified_url": None,
            "page_title": None,
            "parent_source": None,
            "parent_evidence": None,
            "status": "parent_not_verified",
        }

    homepage_url = homepage.url

    soup = BeautifulSoup(homepage.text, "html.parser")

    page_title = None

    if soup.title:
        page_title = clean_text(
            soup.title.get_text(" ")
        )

    # --------------------------------------------------
    # 1. Check homepage
    # --------------------------------------------------

    print(f"Checking: {homepage_url}")

    homepage_text = extract_text(homepage)

    evidence = find_parent_evidence(
        homepage_text,
        parent,
        parent_np
    )

    if evidence:
        print("Parent verified on homepage.")

        return {
            "domain": domain,
            "name": name,
            "parent": parent,
            "verified_url": homepage_url,
            "page_title": page_title,
            "parent_source": homepage_url,
            "parent_evidence": evidence,
            "status": "parent_verified",
        }

    # --------------------------------------------------
    # 2. Find relevant internal pages
    # --------------------------------------------------

    relevant_links = get_relevant_links(homepage)

    print(
        f"Relevant internal pages found: "
        f"{len(relevant_links)}"
    )

    # --------------------------------------------------
    # 3. Check relevant internal pages
    # --------------------------------------------------

    for url in relevant_links:

        print(f"Checking: {url}")

        response = fetch_page(url)

        if not response:
            continue

        text = extract_text(response)

        evidence = find_parent_evidence(
            text,
            parent,
            parent_np
        )

        if evidence:
            print("Parent verified.")

            return {
                "domain": domain,
                "name": name,
                "parent": parent,
                "verified_url": homepage_url,
                "page_title": page_title,
                "parent_source": response.url,
                "parent_evidence": evidence,
                "status": "parent_verified",
            }

    # --------------------------------------------------
    # 4. Parent could not be verified
    # --------------------------------------------------

    print("Parent could not be verified.")

    return {
        "domain": domain,
        "name": name,
        "parent": parent,
        "verified_url": homepage_url,
        "page_title": page_title,
        "parent_source": None,
        "parent_evidence": None,
        "status": "parent_not_verified",
    }


def main():
    results = []

    for site in SITES:
        results.append(
            process_site(site)
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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

    verified = sum(
        1
        for result in results
        if result["status"] == "parent_verified"
    )

    not_verified = len(results) - verified

    print("\n--------------------------------")
    print(f"Created: {OUTPUT_FILE}")
    print(f"Sites processed: {len(results)}")
    print(f"Parent verified: {verified}")
    print(f"Parent not verified: {not_verified}")
    print("--------------------------------")


if __name__ == "__main__":
    main()