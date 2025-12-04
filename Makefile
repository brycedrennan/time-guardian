SHELL := /bin/bash

init: install-uv ## Setup a dev environment for local development.
	uv sync --all-extras
	@echo -e "\nEnvironment setup! ✨ 🍰 ✨ 🐍 \n"
	@echo -e "The following commands are available to run in the Makefile\n"
	@make -s help

afu: autoformat
af: autoformat  ## Alias for `autoformat`
autoformat:  ## Run the autoformatter.
	@uv run -- ruff check . --fix-only --unsafe-fixes
	@uv run -- ruff format .

lint:  ## Run the code linter.
	@uv run -- ruff check .
	@echo -e "✅ No linting errors - well done! ✨ 🍰 ✨"

typecheck: ## Run the type checker.
	@uv run -- ty check
	@echo -e "✅ No type errors - well done! ✨ 🍰 ✨"

test:  ## Run the tests.
	@uv run -- pytest
	@echo -e "✅ The tests pass! ✨ 🍰 ✨"

check: afu lint typecheck test ## Run all checks.

checku: check

version:  ## Show the current version (from git tags).
	@uv run -- python -c "from time_guardian._version import __version__; print(__version__)"

build:  ## Build the package distribution files.
	@echo -e "\n\033[0;34m📦 Building package...\033[0m\n"
	@rm -rf dist build *.egg-info
	@# Rewrite relative image URLs to absolute GitHub raw URLs for PyPI
	@sed -i.bak 's|src="docs/|src="https://raw.githubusercontent.com/brycedrennan/time-guardian/master/docs/|g' README.md
	@uv run -- python -m build
	@# Restore original README
	@mv README.md.bak README.md
	@echo -e "\033[0;32m✅ Build complete! Files in dist/\033[0m\n"
	@ls -la dist/

publish: build  ## Build and upload the package to PyPI.
	@echo -e "\n\033[0;34m📤 Uploading to PyPI...\033[0m\n"
	@uv run -- twine upload dist/* --repository pypi -u __token__
	@echo -e "\n\033[0;32m✅ 📦 Package published successfully to pypi! ✨ 🍰 ✨\033[0m\n"

publish-test: build  ## Build and upload to TestPyPI (for testing).
	@echo -e "\n\033[0;34m📤 Uploading to TestPyPI...\033[0m\n"
	@uv run -- twine upload dist/* --repository testpypi -u __token__
	@echo -e "\n\033[0;32m✅ 📦 Package published to TestPyPI! ✨\033[0m\n"
	@echo -e "Install with: pip install -i https://test.pypi.org/simple/ time-guardian"

release:  ## Create a new release (usage: make release tag=0.1.0)
	@if [ -z "$(tag)" ]; then \
		echo -e "\033[0;31m❌ Error: Version not specified. Usage: make release tag=0.1.0\033[0m"; \
		exit 1; \
	fi
	@echo -e "\n\033[0;34m🏷️  Creating release $(tag)...\033[0m\n"
	@git tag -a "$(tag)" -m "Release $(tag)"
	@echo -e "\033[0;32m✅ Tag $(tag) created locally\033[0m"
	@echo -e "\nTo publish this release:"
	@echo -e "  1. Push the tag:  git push origin $(tag)"
	@echo -e "  2. Publish:       make publish\n"

install-uv:  # Install uv if not already installed
	@if ! uv --help >/dev/null 2>&1; then \
		echo "Installing uv..."; \
		wget -qO- https://astral.sh/uv/install.sh | sh; \
		echo -e "\033[0;32m ✔️  uv installed \033[0m"; \
	fi

help: ## Show this help message.
	@## https://gist.github.com/prwhite/8168133#gistcomment-1716694
	@echo -e "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)" | sort
