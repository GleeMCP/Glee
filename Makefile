.PHONY: install sync test lint clean version patch minor major push publish

# Get current version from pyproject.toml
CURRENT_VERSION := $(shell grep -m1 'version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Install dependencies
install:
	uv sync

sync: install

# Test
test:
	uv run --extra dev pytest -v

# Type check
lint:
	uv run pyright glee/

# Clean
clean:
	rm -rf .venv __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Version management
version:
	@if [ -z "$(filter patch minor major,$(MAKECMDGOALS))" ]; then \
		echo "Usage: make version <patch|minor|major>"; \
		echo "Current version: $(CURRENT_VERSION)"; \
		exit 1; \
	fi

patch minor major: version
	@TYPE=$@ && \
	echo "Current version: $(CURRENT_VERSION)" && \
	NEW_VERSION=$$(echo "$(CURRENT_VERSION)" | awk -F. -v type="$$TYPE" '{ \
		if (type == "major") { print $$1+1".0.0" } \
		else if (type == "minor") { print $$1"."$$2+1".0" } \
		else { print $$1"."$$2"."$$3+1 } \
	}') && \
	echo "New version: $$NEW_VERSION" && \
	sed -i '' 's/version = "$(CURRENT_VERSION)"/version = "'$$NEW_VERSION'"/' pyproject.toml && \
	uv sync && \
	git add pyproject.toml uv.lock && \
	git commit -m "chore: bump version to v$$NEW_VERSION" && \
	git tag "v$$NEW_VERSION" && \
	echo "Created tag v$$NEW_VERSION" && \
	echo "Run 'make push' to push changes and trigger release"

push:
	git push origin main --tags

# Publish to PyPI
publish:
	rm -rf dist/ && uv build && uv publish
