from pathlib import Path

from profiler import pipeline

FIXTURES = Path(__file__).parent / "fixtures"
STATIC = (FIXTURES / "static_portfolio.html").read_text(encoding="utf-8")
SHELL = (FIXTURES / "js_shell.html").read_text(encoding="utf-8")


def test_static_site_never_starts_a_browser(monkeypatch):
    monkeypatch.setattr(pipeline.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(pipeline, "fetch_html", lambda url: STATIC)

    def no_browser(*args, **kwargs):
        raise AssertionError("browser should not be needed for a static site")

    monkeypatch.setattr(pipeline, "BrowserSession", no_browser)

    pages, used_browser = pipeline.collect_pages("https://janedoe.dev/", max_pages=3, progress=lambda m: None)
    assert not used_browser
    assert list(pages) == ["https://janedoe.dev/", "https://janedoe.dev/about", "https://janedoe.dev/projects/"]


def test_js_shell_switches_to_browser_and_closes_it(monkeypatch):
    monkeypatch.setattr(pipeline.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(pipeline, "fetch_html", lambda url: SHELL)
    opened = []

    class FakeBrowser:
        def __init__(self):
            self.closed = False
            opened.append(self)

        def get_html(self, url):
            return STATIC

        def close(self):
            self.closed = True

    monkeypatch.setattr(pipeline, "BrowserSession", FakeBrowser)

    pages, used_browser = pipeline.collect_pages("https://janedoe.dev/", max_pages=2, progress=lambda m: None)
    assert used_browser
    assert "Senior Data Engineer" in pages["https://janedoe.dev/"]
    assert opened[0].closed


def test_merge_pages_drops_repeated_long_lines():
    long_line = "This sentence appears on both pages and is long."
    merged = pipeline.merge_pages({"a": f"{long_line}\nHi", "b": f"{long_line}\nHi"})
    assert merged.count(long_line) == 1
    assert merged.count("Hi") == 2  # short lines are kept


def test_normalize_url():
    assert pipeline.normalize_url("drbipinnepal.com") == "https://drbipinnepal.com"
    assert pipeline.normalize_url("http://x.dev") == "http://x.dev"
