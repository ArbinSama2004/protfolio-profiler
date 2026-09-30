.PHONY: setup app run test clean

setup:
	uv sync

app:
	uv run streamlit run frontend/app.py

# usage: make run URL=https://example.com
run:
	uv run profiler $(URL)

test:
	uv run pytest -q

clean:
	rm -rf output .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
