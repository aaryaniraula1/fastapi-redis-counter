import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

INPUT_FILE = OUTPUT_DIR / "discovered_sites.json"
OUTPUT_FILE = OUTPUT_DIR / "final_hierarchy.json"

MODEL = "gemini-3.7-flash"

TEST_DOMAINS = [
    "cfsc.gov.np",
    "dofsc.gov.np",
    "fpdb.gov.np",
    "frtc.gov.np",
    "redd.gov.np",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/152.0 Safari/537.36"
    )
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OrganisationResult(BaseModel):
    name: str
    hierarchy_names: list[str]


class ParentResult(BaseModel):
    parent_found: bool
    parent_name: str
    parent_domain: str


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_domain(value):
    value = clean_text(value).lower()

    if not value:
        return ""

    if "://" in value:
        value = urlparse(value).netloc.lower()

    if value.startswith("www."):
        value = value[4:]

    return value.split(":")[0].rstrip("/")


def unique(values):
    result = []
    seen = set()

    for value in values:
        value = clean_text(value)

        if value and value.lower() not in seen:
            seen.add(value.lower())
            result.append(value)

    return result


def load_sites():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = (
            data.get("sites")
            or data.get("results")
            or data.get("data")
            or []
        )

    if not isinstance(data, list):
        raise RuntimeError(
            "discovered_sites.json must contain a list of sites."
        )

    sites = []
    seen_domains = set()

    for item in data:
        if not isinstance(item, dict):
            continue

        domain = normalize_domain(
            item.get("domain")
            or item.get("url")
            or item.get("site")
        )

        title = clean_text(
            item.get("title")
            or item.get("name")
            or item.get("discovered_title")
        )

        if not domain or domain in seen_domains:
            continue

        seen_domains.add(domain)

        sites.append({
            "domain": domain,
            "title": title,
        })

    return sites


def request_page(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10,
            allow_redirects=True,
        )
        response.raise_for_status()
        return response

    except requests.RequestException:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10,
                allow_redirects=True,
                verify=False,
            )
            response.raise_for_status()
            return response

        except requests.RequestException:
            return None


def fetch_homepage(domain):
    urls = [
        f"https://{domain}/",
        f"https://www.{domain}/",
        f"http://{domain}/",
        f"http://www.{domain}/",
    ]

    for url in urls:
        response = request_page(url)

        if response is not None:
            return response

    return None


def make_soup(response):
    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def find_branding_area(soup):
    selectors = [
        "header",
        ".site-header",
        ".main-header",
        ".header",
        "#header",
        ".top-header",
        ".branding",
        ".site-branding",
    ]

    for selector in selectors:
        element = soup.select_one(selector)

        if element is not None:
            return element

    return soup


def extract_branding(response):
    soup = make_soup(response)
    area = find_branding_area(soup)

    title = ""

    if soup.title:
        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

    headings = []

    for tag in area.find_all(
        ["h1", "h2", "h3", "h4"]
    ):
        text = clean_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        if 2 <= len(text) <= 180:
            headings.append(text)

    if not headings:
        for tag in soup.find_all(
            ["h1", "h2", "h3"],
            limit=12,
        ):
            text = clean_text(
                tag.get_text(
                    " ",
                    strip=True,
                )
            )

            if 2 <= len(text) <= 180:
                headings.append(text)

    logo_text = []

    for image in area.find_all("img"):
        for field in ("alt", "title"):
            text = clean_text(
                image.get(field)
            )

            if 2 <= len(text) <= 120:
                logo_text.append(text)

    return {
        "title": title,
        "headings": unique(headings)[:10],
        "logo_text": unique(logo_text)[:8],
    }


def find_english_page(response):
    soup = make_soup(response)

    original_domain = normalize_domain(
        response.url
    )

    for link in soup.find_all(
        "a",
        href=True,
    ):
        text = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        ).lower()

        href = clean_text(
            link.get("href")
        )

        if not href:
            continue

        href_lower = href.lower().rstrip("/")

        is_english = (
            text in {"english", "en"}
            or href_lower.endswith("/en")
            or "/en/" in href_lower
        )

        if not is_english:
            continue

        url = urljoin(
            response.url,
            href,
        )

        if normalize_domain(url) != original_domain:
            continue

        page = request_page(url)

        if page is not None:
            return page

    return None


def collect_evidence(domain):
    response = fetch_homepage(domain)

    if response is None:
        raise RuntimeError(
            "Website could not be fetched."
        )

    original = extract_branding(
        response
    )

    english_page = find_english_page(
        response
    )

    if english_page is not None:
        english = extract_branding(
            english_page
        )

        useful_english = (
            bool(english["title"])
            and (
                len(english["headings"]) >= 2
                or bool(english["logo_text"])
            )
        )

        if useful_english:
            return english

    return original


def get_candidate_identity(site):
    domain = site["domain"]

    identity = {
        "domain": domain,
        "title": site.get("title", ""),
        "current_title": "",
        "final_domain": "",
        "canonical_domain": "",
    }

    response = fetch_homepage(domain)

    if response is None:
        return identity

    soup = make_soup(response)

    if soup.title:
        identity["current_title"] = clean_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

    identity["final_domain"] = normalize_domain(
        response.url
    )

    canonical = soup.find(
        "link",
        rel="canonical",
    )

    if (
        canonical is not None
        and canonical.get("href")
    ):
        canonical_url = urljoin(
            response.url,
            canonical.get("href"),
        )

        identity["canonical_domain"] = normalize_domain(
            canonical_url
        )

    return identity


def build_candidates(sites):
    return [
        get_candidate_identity(site)
        for site in sites
    ]


def create_client():
    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set."
        )

    from google import genai

    return genai.Client(
        api_key=api_key
    )


def get_output_text(interaction):
    text = getattr(
        interaction,
        "output_text",
        None,
    )

    if not text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return text.strip()


def extract_organisation(
    client,
    domain,
    discovered_title,
    evidence,
):
    payload = {
        "domain": domain,
        "discovered_title": discovered_title,
        "branding": {
            "title": evidence["title"],
            "headings": evidence["headings"],
            "logo_text": evidence["logo_text"],
        },
    }

    instruction = """
Use only the supplied branding evidence.

Identify the target government organisation and its visible hierarchy.

Return the clean organisation name and hierarchy_names from highest
organisation to target.

Ignore locations, addresses, notices, news, tenders, navigation, slogans
and flags. Do not invent missing hierarchy levels.

Use the official English organisation name when clearly supported.
Otherwise keep the supported name.
"""

    prompt = (
        instruction.strip()
        + "\n\nInput:\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    interaction = client.interactions.create(
        model=MODEL,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": OrganisationResult.model_json_schema(),
        },
    )

    result = OrganisationResult.model_validate_json(
        get_output_text(
            interaction
        )
    )

    name = clean_text(
        result.name
    )

    hierarchy = unique(
        result.hierarchy_names
    )

    if not name:
        raise RuntimeError(
            "Organisation name was not extracted."
        )

    if not hierarchy:
        raise RuntimeError(
            "Organisation hierarchy was not extracted."
        )

    return {
        "name": name,
        "hierarchy_names": hierarchy,
    }


def extract_parent(
    client,
    domain,
    organisation,
    candidates,
):
    payload = {
        "target": {
            "domain": domain,
            "name": organisation["name"],
        },
        "hierarchy_names": organisation["hierarchy_names"],
        "candidate_sites": candidates,
    }

    instruction = """
Find the target's direct parent using only hierarchy_names.

candidate_sites are only for matching the parent's website after the
parent has been identified. Do not infer hierarchy from candidate_sites.

Return the immediate parent only. Do not skip hierarchy levels.

If the matched candidate clearly provides the official English name of
that parent, return the clean English name. Otherwise keep the supported
parent name.

Return parent_domain only when the match is clear. If the parent is known
but its domain is ambiguous or missing, leave parent_domain empty.

If the direct parent cannot be established, set parent_found to false.
"""

    prompt = (
        instruction.strip()
        + "\n\nInput:\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    interaction = client.interactions.create(
        model=MODEL,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ParentResult.model_json_schema(),
        },
    )

    result = ParentResult.model_validate_json(
        get_output_text(
            interaction
        )
    )

    parent_name = clean_text(
        result.parent_name
    )

    parent_domain = normalize_domain(
        result.parent_domain
    )

    valid_domains = {
        normalize_domain(
            item["domain"]
        )
        for item in candidates
    }

    if (
        parent_domain
        and parent_domain not in valid_domains
    ):
        parent_domain = ""

    if (
        not result.parent_found
        or not parent_name
    ):
        return {
            "parent_found": False,
            "parent_name": "",
            "parent_domain": "",
        }

    return {
        "parent_found": True,
        "parent_name": parent_name,
        "parent_domain": parent_domain,
    }


def make_result(
    domain,
    name,
    parent=None,
    status="error",
):
    parent_name = None
    parent_domain = None

    if parent:
        parent_name = (
            parent.get("parent_name")
            or None
        )

        parent_domain = (
            parent.get("parent_domain")
            or None
        )

    return {
        "domain": domain,
        "name": name or None,
        "parent_name": parent_name,
        "parent_domain": parent_domain,
        "parent_url": (
            f"https://{parent_domain}/"
            if parent_domain
            else None
        ),
        "status": status,
    }


def select_sites(
    sites,
    domain=None,
):
    if domain:
        domain = normalize_domain(
            domain
        )

        return [
            site
            for site in sites
            if site["domain"] == domain
        ]

    wanted = set(
        TEST_DOMAINS
    )

    return [
        site
        for site in sites
        if site["domain"] in wanted
    ]


def run_check(sites):
    print("\nPRE-FLIGHT CHECK")
    print("Gemini API calls: 0\n")

    for site in sites:
        domain = site["domain"]

        print("=" * 60)
        print(domain)
        print("=" * 60)

        try:
            evidence = collect_evidence(
                domain
            )

            print("Fetch: OK")
            print(
                "Title:",
                evidence["title"],
            )

            print("Headings:")

            for value in evidence["headings"]:
                print(" -", value)

            print("Logo text:")

            for value in evidence["logo_text"]:
                print(" -", value)

        except Exception as error:
            print("Fetch: ERROR")
            print(
                type(error).__name__,
                str(error),
            )

        print()

    print("Gemini API calls: 0")
    print(
        "final_hierarchy.json was not modified."
    )


def save_results(results):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--domain",
        help="Process one discovered domain",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check extraction without Gemini",
    )

    args = parser.parse_args()

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    sites = load_sites()

    if not sites:
        raise RuntimeError(
            "No sites were loaded from discovered_sites.json."
        )

    selected = select_sites(
        sites,
        args.domain,
    )

    if not selected:
        raise RuntimeError(
            "No matching sites found."
        )

    if args.check:
        run_check(
            selected
        )
        return

    client = create_client()

    print(
        f"Loading {len(sites)} discovered "
        "site identities..."
    )

    candidates = build_candidates(
        sites
    )

    results = []

    for site in selected:
        domain = site["domain"]
        fallback_name = site.get(
            "title",
            "",
        )

        print(
            f"\nProcessing: {domain}"
        )

        try:
            print(
                "1. Extracting small branding evidence..."
            )

            evidence = collect_evidence(
                domain
            )

            print(
                "2. Gemini call 1: "
                "organisation and hierarchy..."
            )

            organisation = extract_organisation(
                client,
                domain,
                fallback_name,
                evidence,
            )

            name = organisation["name"]

            print(
                "   Organisation:",
                name,
            )

            print(
                "   Hierarchy:"
            )

            for hierarchy_name in organisation[
                "hierarchy_names"
            ]:
                print(
                    "   -",
                    hierarchy_name,
                )

            print(
                "3. Gemini call 2: "
                "direct parent..."
            )

            parent = extract_parent(
                client,
                domain,
                organisation,
                candidates,
            )

            if parent["parent_found"]:
                print(
                    "   Parent:",
                    parent["parent_name"],
                )

                if parent["parent_domain"]:
                    print(
                        "   Parent domain:",
                        parent["parent_domain"],
                    )
                else:
                    print(
                        "   Parent domain: unresolved"
                    )

                status = "verified"

            else:
                print(
                    "   Parent: unverified"
                )

                status = "unverified"

            results.append(
                make_result(
                    domain=domain,
                    name=name,
                    parent=parent,
                    status=status,
                )
            )

        except Exception as error:
            print(
                "   Error:",
                type(error).__name__,
                str(error),
            )

            results.append(
                make_result(
                    domain=domain,
                    name=fallback_name,
                    status="error",
                )
            )

    save_results(
        results
    )

    verified = sum(
        item["status"] == "verified"
        for item in results
    )

    unverified = sum(
        item["status"] == "unverified"
        for item in results
    )

    errors = sum(
        item["status"] == "error"
        for item in results
    )

    print(
        f"\nCreated: {OUTPUT_FILE}"
    )

    print(
        f"Sites processed: {len(results)}"
    )

    print(
        f"Verified: {verified}"
    )

    print(
        f"Unverified: {unverified}"
    )

    print(
        f"Errors: {errors}"
    )


if __name__ == "__main__":
    main()