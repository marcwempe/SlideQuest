.PHONY: run dev sync

LOG_DIR := logs
DEV_LOG := $(LOG_DIR)/dev.log

run:
	uv run slidequest

dev:
	rm -f $(DEV_LOG)
	mkdir -p $(LOG_DIR)
	uv run slidequest-dev 2>&1 | tee $(DEV_LOG)
	@echo "--- Logprüfung (\"error\") ---"
	@if grep -qi "error" $(DEV_LOG); then \
		echo "Fehlerhinweise gefunden. Siehe $(DEV_LOG)."; \
	else \
		echo "Keine Fehlerhinweise im Log gefunden."; \
	fi

sync:
	uv sync

test:
	QT_QPA_PLATFORM=offscreen uv run pytest -q
