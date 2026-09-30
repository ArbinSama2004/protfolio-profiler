"""Plain HTTP fetching with requests. Fast, but cannot run JavaScript."""

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-profiler/0.1)"}


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text
