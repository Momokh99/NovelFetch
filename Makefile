# ==============================================================================
# NovelFetch – Development Makefile
# ==============================================================================

.DEFAULT_GOAL := help
.PHONY: help setup setup-tui setup-android lint lint-fix format format-check test test-quick test-android run-tui run-kivy run-kivy-dev

help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ ────────────────────── Environment Setup

setup: setup-tui setup-android  ## Create both development environments
	@echo "✅ Development environments ready: myenv (TUI/tools), android_env (Kivy/tests)"

setup-tui:  ## Create myenv for the TUI and code-quality tools
	python3 -m venv myenv
	./myenv/bin/pip install --upgrade pip
	./myenv/bin/pip install -r requirements.txt
	./myenv/bin/pip install ruff mypy pyright pre-commit
	@echo "✅ TUI environment ready. Activate with: source myenv/bin/activate"

setup-android:  ## Create android_env with system Kivy and GUI/UI test tools
	python3 -m venv --system-site-packages android_env
	./android_env/bin/pip install --upgrade pip
	./android_env/bin/pip install -r gui/requirements.txt
	./android_env/bin/pip install pytest pytest-cov watchdog
	@echo "✅ GUI environment ready. Activate with: source android_env/bin/activate"
	@echo "   Arch Linux requires the system package: sudo pacman -S python-kivy"

##@ ────────────────────── Linting & Formatting

lint:  ## Run Ruff, mypy, and Pyright using myenv
	./myenv/bin/ruff check .
	./myenv/bin/mypy gui/ sources/ --ignore-missing-imports
	./myenv/bin/pyright

lint-fix:  ## Auto-fix lint issues
	./myenv/bin/ruff check --fix .

format:  ## Format code (ruff format + import sorting)
	./myenv/bin/ruff format .
	./myenv/bin/ruff check --fix --select I .

format-check:  ## Check formatting without modifying
	./myenv/bin/ruff format --check .
	./myenv/bin/ruff check --select I . --diff

##@ ────────────────────── Testing

test:  ## Run all tests with coverage in android_env
	./android_env/bin/pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

test-quick:  ## Run tests without coverage (fast)
	./android_env/bin/pytest tests/ -x -q

test-android:  ## Run only Android/UI-related tests
	./android_env/bin/pytest tests/ -v -k "android or ui" --tb=short

##@ ────────────────────── Desktop Development

run-tui:  ## Run the Textual TUI app using myenv
	./myenv/bin/python main.py

run-kivy:  ## Run the KivyMD GUI app using android_env
	./android_env/bin/python gui/main.py

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
	./myenv/bin/pre-commit install

pre-commit-run:  ## Run pre-commit on all files
	./myenv/bin/pre-commit run --all-files

##@ ────────────────────── Cleanup

clean:  ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/
	rm -rf .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
