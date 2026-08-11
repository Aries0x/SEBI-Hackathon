"""
MarketTrust AI — Email Parser.

Parses .eml files to extract headers, body, URLs, and performs
SPF/DKIM/DMARC authentication checks.
"""

from __future__ import annotations

import email
import email.policy
import logging
import re
from typing import Any, Dict, List, Optional
from email import headerregistry

logger = logging.getLogger(__name__)

# URL pattern
URL_REGEX = re.compile(
    r"https?://[^\s<>\"')\]]+",
    re.IGNORECASE,
)


def parse_eml(eml_content: bytes) -> Dict[str, Any]:
    """
    Parse a raw .eml file and extract all relevant information.

    Args:
        eml_content: Raw bytes of the .eml file.

    Returns:
        Dict with headers, body, URLs, and raw structure.
    """
    msg = email.message_from_bytes(eml_content, policy=email.policy.default)

    # Extract headers
    headers = {
        "from": str(msg.get("From", "")),
        "to": str(msg.get("To", "")),
        "cc": str(msg.get("Cc", "")),
        "subject": str(msg.get("Subject", "")),
        "date": str(msg.get("Date", "")),
        "message_id": str(msg.get("Message-ID", "")),
        "reply_to": str(msg.get("Reply-To", "")),
        "return_path": str(msg.get("Return-Path", "")),
        "received": [str(h) for h in msg.get_all("Received", [])],
        "x_mailer": str(msg.get("X-Mailer", "")),
    }

    # Authentication headers
    auth_headers = {
        "dkim_signature": str(msg.get("DKIM-Signature", "")),
        "authentication_results": str(msg.get("Authentication-Results", "")),
        "received_spf": str(msg.get("Received-SPF", "")),
    }

    # Extract body
    body = extract_body(msg)

    # Extract URLs from body
    urls = extract_urls(body["text"] + " " + body.get("html", ""))

    return {
        "headers": headers,
        "auth_headers": auth_headers,
        "body": body,
        "urls": urls,
        "attachments": _list_attachments(msg),
    }


def extract_body(msg: email.message.EmailMessage) -> Dict[str, str]:
    """Extract plain text and HTML body from email message."""
    text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                continue

            if content_type == "text/plain":
                try:
                    text_body += part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_body += payload.decode("utf-8", errors="replace")

            elif content_type == "text/html":
                try:
                    html_body += part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body += payload.decode("utf-8", errors="replace")
    else:
        content_type = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True)
            content = payload.decode("utf-8", errors="replace") if payload else ""

        if content_type == "text/plain":
            text_body = content
        elif content_type == "text/html":
            html_body = content
            # Strip HTML tags for text version
            text_body = _strip_html(content)

    return {"text": text_body, "html": html_body}


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from text content."""
    urls = URL_REGEX.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        # Clean trailing punctuation
        url = url.rstrip(".,;:!?)")
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def check_auth(eml_content: bytes) -> Dict[str, Any]:
    """
    Check email authentication (SPF/DKIM/DMARC).

    Parses existing authentication headers and performs
    basic DKIM verification if the dkimpy library is available.
    """
    msg = email.message_from_bytes(eml_content, policy=email.policy.default)
    results: Dict[str, Any] = {
        "spf": {"status": "unknown", "detail": ""},
        "dkim": {"status": "unknown", "detail": ""},
        "dmarc": {"status": "unknown", "detail": ""},
    }

    # Parse Received-SPF header
    spf_header = str(msg.get("Received-SPF", ""))
    if spf_header:
        spf_status = spf_header.split()[0].lower() if spf_header else "unknown"
        results["spf"] = {"status": spf_status, "detail": spf_header}

    # Parse Authentication-Results for DKIM and DMARC
    auth_results = str(msg.get("Authentication-Results", ""))
    if auth_results:
        auth_lower = auth_results.lower()
        if "dkim=" in auth_lower:
            dkim_match = re.search(r"dkim=(\w+)", auth_lower)
            if dkim_match:
                results["dkim"]["status"] = dkim_match.group(1)
                results["dkim"]["detail"] = auth_results

        if "dmarc=" in auth_lower:
            dmarc_match = re.search(r"dmarc=(\w+)", auth_lower)
            if dmarc_match:
                results["dmarc"]["status"] = dmarc_match.group(1)
                results["dmarc"]["detail"] = auth_results

    # Try DKIM verification with dkimpy
    try:
        import dkim

        dkim_valid = dkim.verify(eml_content)
        results["dkim"]["verified"] = dkim_valid
        if results["dkim"]["status"] == "unknown":
            results["dkim"]["status"] = "pass" if dkim_valid else "fail"
    except ImportError:
        results["dkim"]["verified"] = None
        results["dkim"]["detail"] += " (dkimpy not installed)"
    except Exception as e:
        results["dkim"]["verified"] = None
        results["dkim"]["detail"] += f" (verification error: {e})"

    return results


def _list_attachments(msg: email.message.EmailMessage) -> List[Dict[str, str]]:
    """List email attachments."""
    attachments = []
    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition:
            filename = part.get_filename() or "unnamed"
            content_type = part.get_content_type()
            size = len(part.get_payload(decode=True) or b"")
            attachments.append({
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size,
            })
    return attachments


def _strip_html(html: str) -> str:
    """Simple HTML tag stripping."""
    from html.parser import HTMLParser
    from io import StringIO

    class MLStripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.reset()
            self.fed: List[str] = []

        def handle_data(self, d):
            self.fed.append(d)

        def get_data(self):
            return " ".join(self.fed)

    stripper = MLStripper()
    stripper.feed(html)
    return stripper.get_data()
