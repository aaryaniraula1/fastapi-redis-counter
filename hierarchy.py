import json
import re
import warnings
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "output" / "discovered_sites.json"
OUTPUT_FILE = BASE_DIR / "output" / "hierarchy.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}

# Test only these 5 sites first.
TEST_DOMAINS = {
    "cfsc.gov.np",
    "dnpwc.gov.np",
    "dofsc.gov.np",
    "fpdb.gov.np",
    "frtc.gov.np",
}

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# TEXT NORMALISATION
# ============================================================

def normalise(text):
    if not text:
        return ""

    text = text.lower()

    replacements = {
        # Government / ministry names
        "government of nepal": "government of nepal",
        "governmentofnepal": "government of nepal",
        "नेपाल सरकार": "government of nepal",

        "ministry of agriculture, forest and environment":
            "ministry of agriculture forest and environment",

        "ministry of agriculture, forests and environment":
            "ministry of agriculture forest and environment",

        "कृषि, वन तथा पर्यावरण मन्त्रालय":
            "ministry of agriculture forest and environment",

        "कृषि वन तथा पर्यावरण मन्त्रालय":
            "ministry of agriculture forest and environment",

        "ministry of forests and environment":
            "ministry of forests and environment",

        "वन तथा वातावरण मन्त्रालय":
            "ministry of forests and environment",

        # Organisations
        "forest research and training centre":
            "forest research and training centre",

        "forest research and training center":
            "forest research and training centre",

        "वन अनुसन्धान तथा प्रशिक्षण केन्द्र":
            "forest research and training centre",

        "department of forests and soil conservation":
            "department of forests and soil conservation",

        "वन तथा भू-संरक्षण विभाग":
            "department of forests and soil conservation",

        "वन तथा भू संरक्षण विभाग":
            "department of forests and soil conservation",

        "department of national parks and wildlife conservation":
            "department of national parks and wildlife conservation",

        "राष्ट्रिय निकुञ्ज तथा वन्यजन्तु संरक्षण विभाग":
            "department of national parks and wildlife conservation",

        "forest product development committee":
            "forest product development committee",

        "वन पैदावार विकास समिति":
            "forest product development committee",

        "community forest study center":
            "community forest study center",

        "community forest study centre":
            "community forest study center",

        "सामुदायिक वन अध्ययन केन्द्र":
            "community forest study center",

        "federal watershed management resource center":
            "federal watershed management resource center",

        "federal water management resource center":
            "federal watershed management resource center",

        "संघीय जलाधार व्यवस्थापन स्रोत केन्द्र":
            "federal watershed management resource center",

        "national natural resources and finance commission":
            "national natural resources and finance commission",

        "राष्ट्रिय प्राकृतिक स्रोत तथा वित्त आयोग":
            "national natural resources and finance commission",

        "redd implementation centre":
            "redd implementation centre",

        "redd implementation center":
            "redd implementation centre",
    }

    for old, new in replacements.items():
        text = text.replace(old.lower(), new)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


# ============================================================
# LOAD DISCOVERED SITES
# ============================================================

def load_sites():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "discovered_sites.json must contain a list."
        )

    sites = []

    for item in data:
        if not isinstance(item, dict):
            continue

        domain = item.get("domain")

        if not domain:
            continue

        sites.append(
            {
                "domain": domain.strip().lower(),
                "title": item.get("title", "").strip(),
            }
        )

    return sites


# ============================================================
# HTTP
# ============================================================

def fetch(url):
    try:
        response = session.get(
            url,
            timeout=25,
            verify=False,
            allow_redirects=True,
        )

        if response.status_code == 200:
            return response

    except requests.RequestException:
        pass

    return None


# ============================================================
# ENGLISH VERSION DETECTION
# ============================================================

def find_english_url(homepage):
    response = fetch(homepage)

    if not response:
        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    candidates = []

    for tag in soup.find_all("a", href=True):
        href = urljoin(
            response.url,
            tag.get("href")
        )

        text = clean_text(
            tag.get_text(" ", strip=True)
        ).lower()

        href_lower = href.lower()

        if (
            text in {
                "english",
                "eng",
                "en",
                "english version",
            }
            or text.startswith("english")
            or "/en/" in href_lower
            or href_lower.rstrip("/").endswith("/en")
        ):
            if href not in candidates:
                candidates.append(href)

    for candidate in candidates:
        response = fetch(candidate)

        if response:
            return response.url

    return None


# ============================================================
# HEADER EXTRACTION
# ============================================================

def extract_header(url):
    response = fetch(url)

    if not response:
        return None, None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    header = soup.find("header")

    if header:
        text = clean_text(
            header.get_text(" ", strip=True)
        )

        return response.url, text

    # Fallback for sites without <header>
    selectors = [
        ".header",
        "#header",
        ".site-header",
        ".main-header",
        ".top-header",
        ".navbar",
    ]

    for selector in selectors:
        element = soup.select_one(selector)

        if element:
            text = clean_text(
                element.get_text(" ", strip=True)
            )

            if text:
                return response.url, text

    return response.url, None


# ============================================================
# KNOWN ORGANISATION NAMES
# ============================================================

def build_candidate_index(sites):

    known_names = {

        "brcrn.gov.np": [
            "Building a Resilient Churia Region in Nepal",
        ],

        "cfsc.gov.np": [
            "Community Forest Study Center",
            "Community Forest Study Centre",
            "सामुदायिक वन अध्ययन केन्द्र",
        ],

        "dnpwc.gov.np": [
            "Department of National Parks and Wildlife Conservation",
            "राष्ट्रिय निकुञ्ज तथा वन्यजन्तु संरक्षण विभाग",
        ],

        "dofsc.gov.np": [
            "Department of Forests and Soil Conservation",
            "वन तथा भू-संरक्षण विभाग",
        ],

        "etrs.redd.gov.np": [
            "Electronic Tree Registration System",
        ],

        "fpdb.gov.np": [
            "Forest Product Development Committee",
            "वन पैदावार विकास समिति",
        ],

        "frtc.gov.np": [
            "Forest Research and Training Centre",
            "Forest Research and Training Center",
            "वन अनुसन्धान तथा प्रशिक्षण केन्द्र",
        ],

        "fslscbanke.dofsc.gov.np": [
            "Forest Seed Laboratory and Storage Center",
            "Forest Seed Laboratory And Storage Center",
            "वन विउ प्रयोगशाला तथा भण्डारण केन्द्र",
        ],

        "fwmrc.gov.np": [
            "Federal Watershed Management Resource Center",
            "Federal Water Management Resource Center",
            "संघीय जलाधार व्यवस्थापन स्रोत केन्द्र",
        ],

        "mis.cfsc.gov.np": [
            "CFSC MIS",
        ],

        "moafe.gov.np": [
            "Ministry of Agriculture, Forest and Environment",
            "Ministry of Agriculture, Forests and Environment",
            "कृषि, वन तथा पर्यावरण मन्त्रालय",
        ],

        "moald.gov.np": [
            "Ministry of Agriculture, Forest and Environment",
            "Ministry of Agriculture, Forests and Environment",
            "कृषि, वन तथा पर्यावरण मन्त्रालय",
        ],

        "mofe.gov.np": [
            "Ministry of Forests and Environment",
            "वन तथा वातावरण मन्त्रालय",
        ],

        "nfc.redd.gov.np": [
            "NFC REDD Certification System",
        ],

        "nfis.redd.gov.np": [
            "National Forest Information System",
            "राष्ट्रिय वन तथ्याङ्क प्रणाली",
        ],

        "nfpop.dofsc.gov.np": [
            "NFPOP",
        ],

        "nnrfc.gov.np": [
            "National Natural Resources and Finance Commission",
            "राष्ट्रिय प्राकृतिक स्रोत तथा वित्त आयोग",
        ],

        "redd.gov.np": [
            "REDD Implementation Centre",
            "REDD Implementation Center",
        ],

        "seed.redd.gov.np": [
            "Forest Seed Portal",
        ],
    }

    candidates = []

    for site in sites:

        domain = site["domain"]

        names = known_names.get(
            domain,
            [site.get("title", "")]
        )

        normalised_names = {
            normalise(name)
            for name in names
            if name
        }

        candidates.append(
            {
                "domain": domain,
                "title": site.get("title", ""),
                "names": normalised_names,
            }
        )

    return candidates


# ============================================================
# FIND CURRENT ORGANISATION
# ============================================================

def find_current_position(
    current_domain,
    header_text,
    candidates,
):
    text = normalise(header_text)

    for candidate in candidates:

        if candidate["domain"] != current_domain:
            continue

        positions = []

        for name in candidate["names"]:

            if len(name) < 5:
                continue

            position = text.find(name)

            if position >= 0:
                positions.append(position)

        if positions:
            return min(positions)

    return None


# ============================================================
# FIND PARENT FROM HEADER
# ============================================================

def find_parent_from_header(
    current_site,
    header_text,
    candidates,
):
    if not header_text:
        return None

    text = normalise(header_text)

    current_domain = current_site["domain"]

    current_position = find_current_position(
        current_domain,
        header_text,
        candidates,
    )

    if current_position is None:
        return None

    possible_parents = []

    for candidate in candidates:

        if candidate["domain"] == current_domain:
            continue

        for name in candidate["names"]:

            if len(name) < 5:
                continue

            position = text.find(name)

            if position < 0:
                continue

            # Parent must appear before current organisation.
            if position >= current_position:
                continue

            distance = (
                current_position - position
            )

            possible_parents.append(
                {
                    "candidate": candidate,
                    "position": position,
                    "distance": distance,
                }
            )

    if not possible_parents:
        return None

    possible_parents.sort(
        key=lambda item: item["distance"]
    )

    return possible_parents[0]["candidate"]


# ============================================================
# RELEVANT INTERNAL PAGES
# ============================================================

def find_relevant_pages(
    homepage_url,
    max_pages=8,
):
    response = fetch(homepage_url)

    if not response:
        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    base_domain = urlparse(
        response.url
    ).netloc.lower()

    priority_terms = [
        "introduction",
        "about",
        "organization",
        "organisation",
        "structure",
        "organogram",
        "organization-chart",
        "organization-structure",
        "background",
        "formation",
        "our-team",
    ]

    pages = []

    for link in soup.find_all("a", href=True):

        href = urljoin(
            response.url,
            link.get("href")
        )

        if urlparse(href).netloc.lower() != base_domain:
            continue

        text = clean_text(
            link.get_text(" ", strip=True)
        ).lower()

        combined = (
            text + " " + href.lower()
        )

        if any(
            term in combined
            for term in priority_terms
        ):
            if href not in pages:
                pages.append(href)

    return pages[:max_pages]


# ============================================================
# PROCESS ONE SITE
# ============================================================

def process_site(
    site,
    candidates,
):
    domain = site["domain"]

    homepage = f"https://{domain}/"

    print()
    print("=" * 60)
    print(f"Processing: {domain}")
    print("=" * 60)

    # --------------------------------------------------------
    # Try English version
    # --------------------------------------------------------

    english_url = find_english_url(
        homepage
    )

    if english_url:
        print(
            f"English version found: "
            f"{english_url}"
        )

        header_url = english_url

    else:
        header_url = homepage

    # --------------------------------------------------------
    # Check header
    # --------------------------------------------------------

    print(
        f"Checking header: "
        f"{header_url}"
    )

    actual_url, header_text = extract_header(
        header_url
    )

    if header_text:

        parent = find_parent_from_header(
            site,
            header_text,
            candidates,
        )

        if parent:

            print(
                "Parent found in header: "
                f"{parent['domain']}"
            )

            return {
                "domain": domain,
                "name": site["title"],
                "parent": parent["title"],
                "parent_domain": parent["domain"],
                "parent_source": actual_url,
                "relationship": "parent_identified_from_header",
                "status": "parent_verified",
            }

    print(
        "No parent found in header."
    )

    # --------------------------------------------------------
    # Search relevant pages
    # --------------------------------------------------------

    print(
        "Searching relevant internal pages..."
    )

    pages = find_relevant_pages(
        homepage
    )

    print(
        f"Relevant pages found: "
        f"{len(pages)}"
    )

    for page in pages:

        print(
            f"Checking: {page}"
        )

        page_response = fetch(page)

        if not page_response:
            continue

        soup = BeautifulSoup(
            page_response.text,
            "html.parser"
        )

        text = clean_text(
            soup.get_text(" ", strip=True)
        )

        parent = find_parent_from_header(
            site,
            text,
            candidates,
        )

        if parent:

            print(
                "Parent found on page: "
                f"{parent['domain']}"
            )

            return {
                "domain": domain,
                "name": site["title"],
                "parent": parent["title"],
                "parent_domain": parent["domain"],
                "parent_source": page,
                "relationship": "page_hierarchy",
                "status": "parent_verified",
            }

    print(
        "No parent relationship found "
        "among the discovered sites."
    )

    return {
        "domain": domain,
        "name": site["title"],
        "parent": None,
        "parent_domain": None,
        "parent_source": None,
        "relationship": None,
        "status": "parent_not_verified",
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Loading discovered government sites..."
    )

    all_sites = load_sites()

    print(
        f"Total discovered sites: "
        f"{len(all_sites)}"
    )

    selected_sites = [
        site
        for site in all_sites
        if site["domain"] in TEST_DOMAINS
    ]

    print(
        f"Selected sites for testing: "
        f"{len(selected_sites)}"
    )

    candidates = build_candidate_index(
        all_sites
    )

    print(
        f"Known organisation candidates: "
        f"{len(candidates)}"
    )

    results = []

    for site in selected_sites:

        result = process_site(
            site,
            candidates
        )

        results.append(result)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    verified = sum(
        1
        for result in results
        if result["status"]
        == "parent_verified"
    )

    print()
    print("=" * 40)
    print(
        f"Created: {OUTPUT_FILE}"
    )
    print(
        f"Sites processed: "
        f"{len(results)}"
    )
    print(
        f"Parents verified: "
        f"{verified}"
    )
    print(
        f"Parents not verified: "
        f"{len(results) - verified}"
    )
    print("=" * 40)


if __name__ == "__main__":
    main()