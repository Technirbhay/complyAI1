import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.units import mm


# ============================================================
# CONFIGURATION
# ============================================================

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0 Safari/537.36"
)

GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(exist_ok=True)


# ============================================================
# URL VALIDATION
# ============================================================

def validate_url(url: str) -> str:

    url = url.strip()

    if not url:
        raise ValueError("URL is required.")

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            "Only HTTP and HTTPS URLs are supported."
        )

    if not parsed.netloc:
        raise ValueError(
            "Invalid URL."
        )

    hostname = parsed.hostname

    if not hostname:
        raise ValueError(
            "Invalid URL hostname."
        )

    # --------------------------------------------------------
    # Basic SSRF protection
    # --------------------------------------------------------

    try:

        addresses = socket.getaddrinfo(
            hostname,
            None
        )

        for address in addresses:

            ip = ipaddress.ip_address(
                address[4][0]
            )

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise ValueError(
                    "Private or local URLs are not allowed."
                )

    except socket.gaierror:

        raise ValueError(
            "Unable to resolve the website hostname."
        )

    return url


# ============================================================
# FETCH WEBSITE
# ============================================================

def fetch_webpage(url: str) -> str:

    url = validate_url(url)

    print(
        f"[WEB] Fetching: {url}"
    )

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT
        },
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        ""
    ).lower()

    if "text/html" not in content_type:

        raise ValueError(
            "The provided URL does not return an HTML webpage."
        )

    if not response.text.strip():

        raise ValueError(
            "The webpage returned empty content."
        )

    print(
        f"[WEB] Downloaded "
        f"{len(response.text)} characters"
    )

    return response.text


# ============================================================
# EXTRACT PRIVACY POLICY
# ============================================================

def extract_privacy_policy(
    html: str,
    source_url: str,
) -> str:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # --------------------------------------------------------
    # Remove unnecessary elements
    # --------------------------------------------------------

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "header",
            "footer",
            "aside",
        ]
    ):
        element.decompose()

    # --------------------------------------------------------
    # Try to identify main content
    # --------------------------------------------------------

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(
            "div",
            class_=lambda value:
            value and "privacy" in str(value).lower()
        )
        or soup.body
    )

    if not main:

        raise ValueError(
            "Could not identify readable webpage content."
        )

    text = main.get_text(
        separator="\n",
        strip=True
    )

    # --------------------------------------------------------
    # Clean empty / duplicate lines
    # --------------------------------------------------------

    lines = []

    previous = ""

    for line in text.splitlines():

        line = " ".join(
            line.split()
        ).strip()

        if not line:
            continue

        if line == previous:
            continue

        lines.append(line)

        previous = line

    cleaned_text = "\n".join(lines)

    if len(cleaned_text) < 500:

        raise ValueError(
            "The webpage does not contain enough readable "
            "content to identify a Privacy Policy."
        )

    # --------------------------------------------------------
    # Privacy-policy signal check
    # --------------------------------------------------------

    lower_text = cleaned_text.lower()

    privacy_signals = [
        "privacy policy",
        "personal data",
        "personal information",
        "data protection",
        "cookies",
        "data collection",
        "your rights",
        "retention",
        "third parties",
    ]

    signal_count = sum(
        1
        for signal in privacy_signals
        if signal in lower_text
    )

    if signal_count < 2:

        raise ValueError(
            "This webpage does not appear to be a Privacy Policy."
        )

    # --------------------------------------------------------
    # Limit content for MVP
    # --------------------------------------------------------

    cleaned_text = cleaned_text[:60000]

    print(
        f"[WEB] Extracted privacy policy: "
        f"{len(cleaned_text)} characters"
    )

    return cleaned_text


# ============================================================
# GENERATE PDF
# ============================================================

def generate_policy_pdf(
    policy_text: str,
    source_url: str,
    document_name: str,
) -> str:

    safe_name = "".join(
        character
        if character.isalnum() or character in "-_"
        else "_"
        for character in document_name
    )

    filename = (
        f"{safe_name}_privacy_policy.pdf"
    )

    pdf_path = GENERATED_DIR / filename

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PolicyTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "PolicyHeading",
        parent=styles["Heading2"],
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "PolicyBody",
        parent=styles["BodyText"],
        leading=14,
        spaceAfter=7,
    )

    small_style = ParagraphStyle(
        "PolicySmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    story = []

    story.append(
        Paragraph(
            "ComplyAI Privacy Policy Snapshot",
            title_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Source URL:</b> {source_url}",
            small_style
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            "<b>Generated by:</b> ComplyAI",
            small_style
        )
    )

    story.append(
        Spacer(1, 18)
    )

    story.append(
        Paragraph(
            "Extracted Privacy Policy",
            heading_style
        )
    )

    for paragraph in policy_text.split("\n"):

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        escaped = (
            paragraph
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        story.append(
            Paragraph(
                escaped,
                body_style
            )
        )

    document.build(story)

    print(
        f"[PDF] Generated: {pdf_path}"
    )

    return str(pdf_path)