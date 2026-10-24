.DEFAULT_GOAL := help
PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help install run lint format test check audit scan hooks docker smoke

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install: ## Create .venv and install runtime + dev dependencies
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -q -r requirements-dev.txt

run: ## Start the dev server on $PORT (default 5000)
	$(BIN)/python app.py

lint: ## Ruff lint + format check
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format: ## Apply ruff formatting and safe fixes
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

test: ## Run tests with the coverage gate
	$(BIN)/python -m pytest

check: lint scan test ## Everything CI runs, minus audit and docker
	$(BIN)/python -m py_compile app.py

scan: ## Scan tracked files for committed secrets (values are never printed)
	$(PY) scripts/scan_secrets.py --all

hooks: ## Enable the pre-commit secret scan for this clone
	git config core.hooksPath .githooks

audit: ## Scan dependencies for known vulnerabilities
	$(BIN)/pip-audit -r requirements.txt

docker: ## Build the production image
	docker build -t dealscope:local --build-arg APP_VERSION=$$(git rev-parse --short HEAD) .

smoke: ## Post-deploy smoke check: make smoke URL=https://your-app.onrender.com
	@test -n "$(URL)" || (echo "usage: make smoke URL=https://host" && exit 2)
	bash scripts/smoke.sh "$(URL)"
