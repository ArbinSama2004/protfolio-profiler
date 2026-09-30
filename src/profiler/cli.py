"""Command-line entry point: `uv run profiler https://example.com`."""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from .llm import DEFAULT_MODEL, Profile
from .pipeline import normalize_url, profile_url


def format_summary(profile: Profile) -> str:
    lines = [profile.name or "(name not found)"]
    if profile.headline:
        lines.append(profile.headline)
    if profile.summary:
        lines += ["", profile.summary]
    if profile.skills:
        lines += ["", "Skills: " + ", ".join(profile.skills)]
    if profile.experience:
        lines += ["", "Experience:"]
        for job in profile.experience:
            dates = " - ".join(part for part in (job.start, job.end) if part)
            lines.append(f"  - {job.title or '?'} at {job.company or '?'}" + (f" ({dates})" if dates else ""))
    if profile.projects:
        lines += ["", "Projects: " + ", ".join(p.name for p in profile.projects if p.name)]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(prog="profiler", description="Summarise people from their portfolio sites.")
    parser.add_argument("urls", nargs="+", help="portfolio URL(s)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-pages", type=int, default=5, help="pages to read per site (default: 5)")
    parser.add_argument("--out", type=Path, default=Path("output"), help="folder for JSON results")
    args = parser.parse_args()

    args.out.mkdir(exist_ok=True)
    failures = 0
    for raw_url in args.urls:
        url = normalize_url(raw_url)
        try:
            result = profile_url(url, args.model, args.max_pages, progress=print)
        except Exception as exc:  # keep going so one bad site doesn't stop the batch
            print(f"FAILED {url}: {exc}", file=sys.stderr)
            failures += 1
            continue

        name = re.sub(r"\W+", "_", urlparse(url).netloc.removeprefix("www."))
        path = args.out / f"{name}.json"
        path.write_text(result.profile.model_dump_json(indent=2), encoding="utf-8")
        print(f"\n{format_summary(result.profile)}\n\nSaved {path}\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
