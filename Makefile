.PHONY: run dev sync

run:
	uv run slidequest

dev:
	uv run slidequest-dev

sync:
	uv sync
