# ==============================================================================
# NovelFetch – Development Makefile
# ==============================================================================

.DEFAULT_GOAL := help
.PHONY: help

help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ ────────────────────── Environment Setup

setup:  ## Create venv and install all dev dependencies
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r android_app/requirements.txt
	./venv/bin/pip install ruff mypy pytest pytest-cov watchdog pre-commit
	@echo "✅ Done. Activate with: source venv/bin/activate"

##@ ────────────────────── Linting & Formatting

lint:  ## Run all linters (ruff check + mypy)
	./venv/bin/ruff check .
	./venv/bin/mypy android_app/ sources/ --ignore-missing-imports

lint-fix:  ## Auto-fix lint issues
	./venv/bin/ruff check --fix .

format:  ## Format code (ruff format + ruff import sorting)
	./venv/bin/ruff format .
	./venv/bin/ruff check --fix --select I .

format-check:  ## Check formatting without modifying
	./venv/bin/ruff format --check .
	./venv/bin/ruff check --select I . --diff

##@ ────────────────────── Testing

test:  ## Run all tests with coverage
	./venv/bin/pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

test-quick:  ## Run tests without coverage (fast)
	./venv/bin/pytest tests/ -x -q

test-android:  ## Run only Android-related tests
	./venv/bin/pytest tests/ -v -k "android or ui" --tb=short

##@ ────────────────────── Desktop Development

run-tui:  ## Run the Textual TUI app
	./venv/bin/python main.py

run-kivy:  ## Run the KivyMD app on desktop (no hot-reload)
	cd android_app && ../venv/bin/python main.py

run-kivy-dev:  ## Run the KivyMD app with hot-reload
	DEBUG=1 ./venv/bin/python android_app/main_dev.py

##@ ────────────────────── Android Build

android-debug:  ## Build debug APK
	buildozer android debug

android-release:  ## Build release APK
	buildozer android release

android-deploy:  ## Deploy to connected device
	buildozer android debug deploy run

android-logcat:  ## Show device logcat
	buildozer android logcat

android-clean:  ## Clean buildozer build artifacts
	buildozer android clean

##@ ────────────────────── Code Quality

pre-commit-install:  ## Install pre-commit hooks
	./venv/bin/pre-commit install

pre-commit-run:  ## Run pre-commit on all files
	./venv/bin/pre-commit run --all-files

##@ ────────────────────── Cleanup

clean:  ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/
	rm -rf .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
