.PHONY: run dev sync test --debug

ifneq ($(filter --debug,$(MAKECMDGOALS)),)
DEBUG := 1
endif

LOG_DIR := logs
DEV_LOG := $(LOG_DIR)/dev.log
TORCH_LIB_DIR := $(firstword $(wildcard .venv/lib/python*/site-packages/torch/lib))
FFMPEG_LIB_DIR ?= /opt/homebrew/opt/ffmpeg/lib
ENSURE_TORCH_LIBS := if [ -z "$(TORCH_LIB_DIR)" ]; then \
	>&2 echo "Torch libraries not found (.venv/lib/python*/site-packages/torch/lib). Run 'uv sync' first."; \
	exit 1; \
fi
DYLD_ENV := env DYLD_LIBRARY_PATH="$(TORCH_LIB_DIR):$(FFMPEG_LIB_DIR)$${DYLD_LIBRARY_PATH:+:$$DYLD_LIBRARY_PATH}"

LOG_LEVEL ?= INFO
ifneq ($(strip $(DEBUG)),)
LOG_LEVEL := DEBUG
endif
PY_LOG_ENV := PYTHONLOGLEVEL=$(LOG_LEVEL)

run:
	@$(ENSURE_TORCH_LIBS)
	$(DYLD_ENV) $(PY_LOG_ENV) uv run slidequest

dev:
	rm -f $(DEV_LOG)
	mkdir -p $(LOG_DIR)
	@$(ENSURE_TORCH_LIBS)
	@echo "Starte SlideQuest (Log-Level: $(LOG_LEVEL)) – Ausgabe in $(DEV_LOG)"
	$(DYLD_ENV) $(PY_LOG_ENV) uv run slidequest-dev 2>&1 | tee $(DEV_LOG)
	@echo "--- Logprüfung (\"error\") ---"
	@if grep -qi "error" $(DEV_LOG); then \
		echo "Fehlerhinweise gefunden. Siehe $(DEV_LOG)."; \
	else \
		echo "Keine Fehlerhinweise im Log gefunden."; \
	fi

sync:
	uv sync

test:
	@$(ENSURE_TORCH_LIBS)
	QT_QPA_PLATFORM=offscreen $(DYLD_ENV) uv run pytest -q

--debug:
	@true
