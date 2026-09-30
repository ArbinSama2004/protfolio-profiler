# Portfolio Profiler

Give it a portfolio website. It reads the site, then asks an [Ollama](https://ollama.com) model to answer:
**who is this person, what do they do, and what have they worked on?** The result is structured JSON plus a
simple Streamlit page.

```
URL ──► requests + BeautifulSoup ──► clean text ──┐
          │                                        ├──► Ollama (LLM) ──► validated Profile ──► Streamlit / JSON
          └─ page is an empty JS shell?            │
             ──► Selenium (headless Chrome) ───────┘
```

## How it works

1. **Fetch.** The home page is downloaded with `requests`. That is fast and works for normal HTML sites.
2. **Fall back to a browser.** Many portfolios (React, Next.js, ...) send an empty page and build the content with
   JavaScript. If the text that comes back is nearly empty, the tool switches to **Selenium** (headless Chrome),
   which waits for the page to render and scrolls to load lazy content.
3. **Clean.** **BeautifulSoup** removes scripts, styles, navigation and footers and keeps the readable text. It
   also picks a few same-site links (About, Projects, Experience, ...) and the tool reads those pages too.
4. **Extract.** The combined text goes to the Ollama model with one strict rule: *use only what the site says,
   otherwise answer null.* The model must reply in JSON.
5. **Validate.** The reply is checked against a [Pydantic](https://docs.pydantic.dev) schema (`llm/schema.py`).
   If the JSON is invalid, the model is asked once more before the tool gives up.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Google Chrome (Selenium downloads the matching driver automatically)
- [Ollama](https://ollama.com/download), installed and running

## Setup

```bash
uv sync                        # install dependencies into .venv

# The default model is a cloud model, so sign in once, then pull it:
ollama signin
ollama pull gpt-oss:20b-cloud
```

> **Privacy note:** `*-cloud` models run on Ollama's servers, so the scraped page text is sent there. For a fully
> local run, pull a local model (for example `ollama pull llama3.1:8b`) and choose it in the app or with `--model`.

## Usage

**Web app**

```bash
make app        # or: uv run streamlit run frontend/app.py
```

Paste one or more URLs, pick a model, click **Analyze**. Live status shows each step. Each result can be downloaded
as JSON.

**Command line**

```bash
make run URL=https://example.com      # or: uv run profiler https://example.com
uv run profiler site-one.com site-two.com --model llama3.1:8b --max-pages 3
```

Results are saved to `output/<site>.json`. Run `uv run profiler --help` for all options.

**Settings** (environment variables, all optional): `OLLAMA_URL` (default `http://localhost:11434`) and
`OLLAMA_MODEL` (default `gpt-oss:20b-cloud`).

`make` is only a shortcut. On Windows, run the `uv` commands shown above directly.

## Project layout

```
frontend/app.py                Streamlit page
src/profiler/
├── soup_parser/               requests fetch + BeautifulSoup cleaning and link finding
├── selenium_scraper/          headless Chrome for JavaScript-rendered sites
├── llm/                       Ollama client, prompt, Pydantic Profile schema
├── pipeline.py                URL -> pages -> text -> LLM -> Profile
└── cli.py                     command-line entry point
tests/                         offline tests using saved HTML
```

## Design choices

- **Plain `requests`, no async.** Pages are fetched one at a time on purpose: it is easy to follow, polite to the
  site (there is a 1 second pause between pages), and Selenium is synchronous anyway. The slow step is the LLM
  call, not the downloads.
- **One browser per site.** Selenium starts Chrome only when needed and reuses it for every page of that site.
- **Optional fields.** A missing email or employer stays `null`. The tool would rather say "unknown" than guess.
- **Streamlit calls the pipeline directly.** There is no separate API server, because it would add a layer
  without adding value for a tool this size.

## Tests

```bash
make test       # or: uv run pytest -q
```

The tests cover HTML cleaning, link selection, JS-shell detection, the pipeline's static and browser paths, and
the LLM reply parsing and retry logic. They run offline; the browser and Ollama are replaced by fakes. A real run
against a live site and model is the final check.

## Limitations

- Sites that block automated visitors, or that sit behind a login, will fail or return little text.
- Portfolios that use `#/hash` routes show every page at the same address, so sub-pages are not discovered. The
  home page is still read.
- Very long sites are cut off at about 30,000 characters before they reach the model.
- An LLM can still misread a page. Treat the output as a summary and check it against the site.

## Use it responsibly

This tool is meant for public portfolio pages. Check a site's terms and `robots.txt` before scraping it, keep the
page limit low, and remember that the pages describe real people.
