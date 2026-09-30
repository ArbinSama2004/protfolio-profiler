"""BeautifulSoup helpers: turn raw HTML into clean text and find pages worth visiting."""

from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

# Tags that never contain useful profile text.
NOISE_TAGS = ["script", "style", "noscript", "svg", "iframe", "nav", "footer"]

SKIP_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".doc", ".docx")

# Links containing these words are visited first.
PRIORITY_WORDS = (
    "about", "experience", "work", "project", "resume", "cv", "portfolio",
    "research", "publication", "education", "skill", "career",
)

# Pages with less text than this are probably an empty JavaScript shell.
MIN_TEXT_CHARS = 400


def clean_text(html: str) -> str:
    """Return the readable text of a page, one non-empty line per row."""
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else ""

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return f"{description}\n{text}" if description else text


def is_js_shell(text: str) -> bool:
    """True when the page looks like an empty app shell that needs a real browser."""
    return len(text) < MIN_TEXT_CHARS or "enable javascript" in text.lower()


def find_internal_links(html: str, base_url: str, limit: int = 4) -> list[str]:
    """Same-site links worth visiting, most promising first."""
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc.removeprefix("www.")
    seen = {urldefrag(base_url)[0].rstrip("/")}
    priority: list[str] = []
    others: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        url = urldefrag(urljoin(base_url, href))[0]
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.removeprefix("www.") != base_host:
            continue
        if parsed.path.lower().endswith(SKIP_EXTENSIONS):
            continue

        key = url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)

        label = f"{parsed.path} {anchor.get_text(' ', strip=True)}".lower()
        is_priority = any(word in label for word in PRIORITY_WORDS)
        (priority if is_priority else others).append(url)

    return (priority + others)[:limit]
