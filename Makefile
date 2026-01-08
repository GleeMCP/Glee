.PHONY: install sync dev stdio test d-up d-down d-logs d-build d-codex-auth clean version patch minor major push

# Get current version from pyproject.toml
CURRENT_VERSION := $(shell grep -m1 'version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Install dependencies
install:
	uv sync

sync: install

# Run MCP server (SSE mode for local development)
dev:
	GLEE_TRANSPORT=sse uv run python -m glee

# Run MCP server (stdio mode - called by Claude Code)
stdio:
	uv run python -m glee

# Test
test:
	uv run --extra dev pytest -v

# Database migrations
m:
	uv run alembic upgrade head

m-new:
	@read -p "Migration name: " name; \
	uv run alembic revision -m "$$name"

m-down:
	uv run alembic downgrade -1

# Docker
d-up:
	docker compose up -d

d-down:
	docker compose down

d-logs:
	docker compose logs -f

d-build:
	docker compose build --no-cache

# Codex auth (inside container)
d-codex-auth:
	docker exec -it glee-server codex login --device-auth

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
	git add pyproject.toml && \
	git commit -m "chore: bump version to v$$NEW_VERSION" && \
	git tag "v$$NEW_VERSION" && \
	echo "Created tag v$$NEW_VERSION" && \
	echo "Run 'make push' to push changes and trigger release"

push:
	git push origin main --tags
