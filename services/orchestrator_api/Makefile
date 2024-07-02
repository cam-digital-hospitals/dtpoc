# Setting SHELL to bash allows bash commands to be executed by recipes.
# Options are set to exit when a recipe line exits non-zero or a piped command fails.
SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec
PYTHON := ./.venv/bin/python
PYTHONPATH := `pwd`

.DEFAULT_TARGET=help
# VERSION:=$(shell cat VERSION)


##@ General

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Deps

.venv: ## Create a python3 virtual environment
	python3 -m venv .venv

.PHONY: deps
deps: .venv ## Install dependencies into local virtual environment
	@$(PYTHON) -m pip install pip-tools
	@$(PYTHON) -m piptools compile --upgrade --strip-extras --quiet
	@$(PYTHON) -m piptools sync

.PHONY: clean
clean: ## Cleanup
	rm -rf .venv
	rm -rf requirements*.txt
	rm -rf **/requirements*.txt

##@ Build
build: ## Build image (tag: latest)
	@docker build --tag ghcr.io/cam-digital-hospitals/orchestrator-api:latest .

##@ Release
push_latest: ## Push latest images to ghcr
	@docker push ghcr.io/cam-digital-hospitals/orchestrator-api:latest
