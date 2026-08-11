"""
MarketTrust AI — Website Scraper.

Renders web pages with Playwright, extracts content, takes screenshots,
and checks domain reputation via WHOIS and SSL.
"""

from __future__ import annotations

import logging
import ssl
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _extract_title_from_html(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return soup.title.string.strip() if soup.title and soup.title.string else ""
    except Exception:
        return ""


def _http_fallback_render(url: str) -> Dict[str, Any]:
    logger.info(f"Using HTTP fallback scraper for {url}")
    try:
        import httpx
        from app.website.scraper import extract_html

        with httpx.Client(verify=False, timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            response = client.get(url, headers=headers)
            html_content = response.text
            text_content = extract_html(html_content)
            title = _extract_title_from_html(html_content) or url

            logger.info(f"Fallback HTTP fetch succeeded for {url} with status {response.status_code}")
            return {
                "url": url,
                "final_url": str(response.url),
                "title": title,
                "status_code": response.status_code,
                "redirected": str(response.url) != url,
                "text": text_content,
                "html": html_content,
                "links": [],
                "meta_tags": [],
            }
    except Exception as e:
        logger.error(f"Fallback HTTP fetch failed for {url}: {e}")
        return {"url": url, "error": f"Playwright and fallback failed: {e}", "text": "", "html": ""}


def render_page(url: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Render a web page using Playwright and extract content.

    Args:
        url: The URL to render.
        screenshot_path: Optional path to save a full-page screenshot.

    Returns:
        Dict with html, text, title, and metadata.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            # Navigate with timeout
            response = page.goto(url, wait_until="networkidle", timeout=30000)

            result = {
                "url": url,
                "final_url": page.url,
                "title": page.title(),
                "status_code": response.status if response else None,
                "redirected": page.url != url,
            }

            # Extract visible text
            result["text"] = page.inner_text("body")

            # Extract HTML
            result["html"] = page.content()

            # Take screenshot
            if screenshot_path:
                page.screenshot(path=screenshot_path, full_page=True)
                result["screenshot_path"] = screenshot_path

            # Extract links
            links = page.eval_on_selector_all(
                "a[href]",
                "elements => elements.map(e => ({href: e.href, text: e.textContent.trim()}))",
            )
            result["links"] = links[:100]  # Limit to 100 links

            # Extract meta tags
            meta_tags = page.eval_on_selector_all(
                "meta",
                "elements => elements.map(e => ({name: e.name, content: e.content, property: e.getAttribute('property')}))",
            )
            result["meta_tags"] = meta_tags

            browser.close()
            logger.info(f"Rendered {url}: status={result['status_code']}")
            return result

    except ImportError:
        logger.warning("Playwright not installed, falling back to HTTP fetcher")
        return _http_fallback_render(url)
    except Exception as e:
        logger.error(f"Page render failed for {url}: {e}, falling back to HTTP fetcher")
        return _http_fallback_render(url)


def extract_html(html: str) -> str:
    """
    Extract clean text from HTML using BeautifulSoup.

    Args:
        html: Raw HTML content.

    Returns:
        Clean text content.
    """
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "noscript", "nav", "footer"]):
            element.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    except ImportError:
        logger.warning("BeautifulSoup not installed")
        return html
    except Exception as e:
        logger.error(f"HTML extraction failed: {e}")
        return ""


def check_whois(url: str) -> Dict[str, Any]:
    """
    Check domain WHOIS information.

    Returns dict with domain age, registrar, creation/expiry dates.
    """
    domain = urlparse(url).netloc
    if domain.startswith("www."):
        domain = domain[4:]

    try:
        import whois

        w = whois.whois(domain)

        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        expiration_date = w.expiration_date
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]

        # Calculate domain age
        domain_age_days = None
        if creation_date:
            if isinstance(creation_date, datetime):
                if creation_date.tzinfo is not None:
                    domain_age_days = (datetime.now(timezone.utc) - creation_date.astimezone(timezone.utc)).days
                else:
                    domain_age_days = (datetime.now() - creation_date).days
            else:
                domain_age_days = None

        return {
            "domain": domain,
            "registrar": str(w.registrar) if w.registrar else "Unknown",
            "creation_date": str(creation_date) if creation_date else None,
            "expiration_date": str(expiration_date) if expiration_date else None,
            "domain_age_days": domain_age_days,
            "name_servers": w.name_servers if w.name_servers else [],
            "org": str(w.org) if w.org else None,
            "country": str(w.country) if w.country else None,
            "is_new_domain": domain_age_days is not None and domain_age_days < 90,
        }

    except ImportError:
        logger.warning("python-whois not installed")
        return {"domain": domain, "error": "whois not available"}
    except Exception as e:
        logger.error(f"WHOIS lookup failed for {domain}: {e}")
        return {"domain": domain, "error": str(e)}


def check_ssl(url: str) -> Dict[str, Any]:
    """
    Check SSL certificate validity for a URL.

    Returns dict with cert details, validity, issuer.
    """
    parsed = urlparse(url)
    hostname = parsed.netloc
    port = 443

    if ":" in hostname:
        hostname, port_str = hostname.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = 443

    if parsed.scheme != "https":
        return {
            "hostname": hostname,
            "has_ssl": False,
            "error": "Not HTTPS",
        }

    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                # Parse certificate details
                subject = dict(x[0] for x in cert.get("subject", ()))
                issuer = dict(x[0] for x in cert.get("issuer", ()))
                not_before = cert.get("notBefore", "")
                not_after = cert.get("notAfter", "")

                # Check if cert is still valid
                from email.utils import parsedate_to_datetime

                try:
                    expiry = parsedate_to_datetime(not_after)
                    is_valid = expiry > datetime.now(timezone.utc)
                    days_until_expiry = (expiry - datetime.now(timezone.utc)).days
                except Exception:
                    is_valid = True
                    days_until_expiry = None

                return {
                    "hostname": hostname,
                    "has_ssl": True,
                    "is_valid": is_valid,
                    "subject": subject.get("commonName", ""),
                    "issuer": issuer.get("organizationName", ""),
                    "not_before": not_before,
                    "not_after": not_after,
                    "days_until_expiry": days_until_expiry,
                    "san": [
                        entry[1]
                        for entry in cert.get("subjectAltName", ())
                    ],
                }

    except ssl.SSLCertVerificationError as e:
        return {
            "hostname": hostname,
            "has_ssl": True,
            "is_valid": False,
            "error": f"Certificate verification failed: {e}",
        }
    except Exception as e:
        return {
            "hostname": hostname,
            "has_ssl": False,
            "error": str(e),
        }
