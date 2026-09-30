"""The whole job in one place: URL -> pages -> clean text -> LLM -> Profile."""

import time
from collections.abc import Callable
from dataclasses import dataclass

import requests
from selenium.common.exceptions import WebDriverException

from .llm import DEFAULT_MODEL, Profile, extract_profile
from .selenium_scraper import BrowserSession
from .soup_parser import clean_text, fetch_html, find_internal_links, is_js_shell

Progress = Callable[[str], None]
PAUSE_SECONDS = 1  # be polite between page loads


@dataclass
class ProfileResult:
    url: str
    profile: Profile
    pages: list[str]
    used_browser: bool


def normalize_url(url: str) -> str:
    url = url.strip()
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def collect_pages(url: str, max_pages: int = 5, progress: Progress = print) -> tuple[dict[str, str], bool]:
    """Return ({page_url: clean_text}, used_browser).

    Starts with plain requests; switches to Selenium only if the page is an empty JS shell.
    """
    browser: BrowserSession | None = None
    try:
        try:
            progress(f"Fetching {url}")
            html = fetch_html(url)
            text = clean_text(html)
            needs_browser = is_js_shell(text)
            if needs_browser:
                progress("Page is rendered by JavaScript, switching to the browser")
        except requests.RequestException as exc:
            progress(f"Plain request failed ({exc}), trying the browser")
            needs_browser = True

        if needs_browser:
            browser = BrowserSession()
            html = browser.get_html(url)
            text = clean_text(html)

        pages = {url: text}
        for link in find_internal_links(html, url, limit=max_pages - 1):
            time.sleep(PAUSE_SECONDS)
            progress(f"Fetching {link}")
            try:
                page_html = browser.get_html(link) if browser else fetch_html(link)
            except (requests.RequestException, WebDriverException) as exc:
                progress(f"Skipped {link}: {exc}")
                continue
            pages[link] = clean_text(page_html)
        return pages, browser is not None
    finally:
        if browser:
            browser.close()


def merge_pages(pages: dict[str, str]) -> str:
    """Join pages into one prompt, dropping long lines that repeat across pages."""
    seen: set[str] = set()
    parts = []
    for page_url, text in pages.items():
        lines = [line for line in text.splitlines() if len(line) < 20 or line not in seen]
        seen.update(lines)
        parts.append(f"=== PAGE: {page_url} ===\n" + "\n".join(lines))
    return "\n\n".join(parts)


def profile_url(
    url: str,
    model: str = DEFAULT_MODEL,
    max_pages: int = 5,
    progress: Progress = print,
) -> ProfileResult:
    url = normalize_url(url)
    pages, used_browser = collect_pages(url, max_pages, progress)
    progress(f"Collected {len(pages)} page(s). Asking {model}, this can take a minute")
    profile = extract_profile(merge_pages(pages), model)
    return ProfileResult(url=url, profile=profile, pages=list(pages), used_browser=used_browser)
