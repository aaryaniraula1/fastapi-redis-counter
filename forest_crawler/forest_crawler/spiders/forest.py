import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class ForestSpider(scrapy.Spider):
    name = "forest"

    seed_domains = {
        "mofe.gov.np",
        "moald.gov.np",
        "dofsc.gov.np",
        "dnpwc.gov.np",
        "frtc.gov.np",
        "redd.gov.np",
    }

    accepted_domains = set(seed_domains)

    checked_domains = set()

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

    
    domain_relevance_keywords = [
        "forest",
        "forestry",
        "forests",
        "wildlife",
        "conservation",
        "national park",
        "forest management",
        "forest research",
        "forest training",
        "forestry research",
        "forestry training",
        "biodiversity",
        "trees",
        "natural resources",
        "forest resources",
        "forest department",
        "forest office",
        "frtc",
        "dofsc",
        "dnpwc",
        "redd",
    ]

    # Minimum score required for a candidate domain to become an accepted domain
    DOMAIN_RELEVANCE_THRESHOLD = 3

    def normalize_domain(self, url):
        """
        Extract and normalize the domain from a URL.

        Example:
        https://www.example.gov.np/page
        becomes:
        example.gov.np
        """

        domain = urlparse(url).netloc.lower().split(":")[0]

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    def is_external_gov_domain(self, domain, current_domain):
        """
        Check whether a discovered domain is:

        - a .gov.np domain
        - different from the current domain
        - not already accepted
        - not already checked
        """

        return (
            domain.endswith(".gov.np")
            and domain != current_domain
            and domain not in self.accepted_domains
            and domain not in self.checked_domains
        )

    def calculate_domain_relevance(
        self,
        domain,
        title,
        headings,
        page_text
    ):
        """
        Calculate how relevant a candidate government domain
        is to the forest sector.

        Higher scores indicate stronger relevance.
        """

        domain_text = domain.lower()
        title_text = title.lower()
        headings_text = " ".join(headings).lower()
        content_text = page_text.lower()

        score = 0

        for keyword in self.domain_relevance_keywords:

            if keyword in domain_text:
                score += 2

            if keyword in title_text:
                score += 2

            if keyword in headings_text:
                score += 1

            if keyword in content_text:
                score += 1

        return score

    def parse(self, response):
        """
        Process a page, identify relevant content,
        discover new government domains, and follow
        accepted domains.
        """

        content_type = response.headers.get(
            "Content-Type", b""
        ).decode(
            "utf-8",
            errors="ignore"
        )

        if "text/html" not in content_type:
            return

        current_domain = self.normalize_domain(response.url)

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        
        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else ""
        )

        
        headings = []

        for heading in soup.find_all(
            ["h1", "h2", "h3", "h4"]
        ):
            text = heading.get_text(
                " ",
                strip=True
            )

            if text:
                headings.append(text)

       
        page_text = soup.get_text(
            " ",
            strip=True
        )

       

        if response.meta.get("candidate_domain"):

            candidate_domain = response.meta[
                "candidate_domain"
            ]

        
            score = self.calculate_domain_relevance(
                candidate_domain,
                title,
                headings,
                page_text
            )

           
            self.checked_domains.add(candidate_domain)

            # Accept the domain if it meets the threshold
            if score >= self.DOMAIN_RELEVANCE_THRESHOLD:

                self.accepted_domains.add(
                    candidate_domain
                )

                self.logger.info(
                    "Accepted candidate domain: %s | score: %s",
                    candidate_domain,
                    score
                )

            
            else:

                self.logger.info(
                    "Rejected candidate domain: %s | score: %s",
                    candidate_domain,
                    score
                )

                
                return

       
        text_to_check = (
            title
            + " "
            + " ".join(headings)
            + " "
            + page_text[:10000]
        ).lower()

        relevant = any(
            keyword in text_to_check
            for keyword in self.relevant_keywords
        )

        
        if relevant:

            yield {
                "url": response.url,
                "domain": current_domain,
                "title": title,
                "headings": headings,
                "content": page_text[:5000],
            }

        

        for link in response.css(
            "a::attr(href)"
        ).getall():

            next_url = response.urljoin(link)

            parsed = urlparse(next_url)

            # Ignore non-HTTP/HTTPS links
            if parsed.scheme not in ["http", "https"]:
                continue

            next_domain = self.normalize_domain(
                next_url
            )

            # -----------------------------------------------------
            # A. Already accepted domain
            # -----------------------------------------------------

            if next_domain in self.accepted_domains:

                yield response.follow(
                    next_url,
                    callback=self.parse
                )

            # -----------------------------------------------------
            # B. New external .gov.np candidate
            # -----------------------------------------------------

            elif self.is_external_gov_domain(
                next_domain,
                current_domain
            ):

                
                candidate_url = (
                    f"{parsed.scheme}://{next_domain}"
                )

                yield scrapy.Request(
                    candidate_url,
                    callback=self.parse,
                    meta={
                        "candidate_domain": next_domain
                    },
                    dont_filter=True
                )