from pathlib import Path

from profiler.soup_parser import clean_text, find_internal_links, is_js_shell

FIXTURES = Path(__file__).parent / "fixtures"
STATIC = (FIXTURES / "static_portfolio.html").read_text(encoding="utf-8")
SHELL = (FIXTURES / "js_shell.html").read_text(encoding="utf-8")
BASE = "https://janedoe.dev/"


def test_clean_text_keeps_content_and_drops_noise():
    text = clean_text(STATIC)
    assert "Senior Data Engineer at Acme Analytics" in text
    assert "Python, SQL, Airflow" in text
    for noise in ("SECRET_SCRIPT_TEXT", "color: red", "FOOTER_TEXT", "NOSCRIPT_TEXT", "Blog"):
        assert noise not in text


def test_clean_text_starts_with_meta_description():
    assert clean_text(STATIC).startswith("Jane Doe is a data engineer based in Austin.")


def test_find_internal_links_filters_and_prioritises():
    links = find_internal_links(STATIC, BASE, limit=10)
    assert links == [
        "https://janedoe.dev/about",
        "https://janedoe.dev/projects/",
        "https://janedoe.dev/blog",
    ]


def test_find_internal_links_respects_limit():
    assert len(find_internal_links(STATIC, BASE, limit=2)) == 2
    assert find_internal_links(STATIC, BASE, limit=0) == []


def test_find_internal_links_treats_www_as_same_site():
    links = find_internal_links(STATIC, "https://example.com/", limit=10)
    assert "https://www.example.com/contact" in links
    assert all("github.com" not in link for link in links)


def test_is_js_shell():
    assert is_js_shell(clean_text(SHELL))
    assert not is_js_shell(clean_text(STATIC))
