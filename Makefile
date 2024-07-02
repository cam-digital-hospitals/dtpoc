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

.PHONY: install
install: ## Install helm chart into the default k8s cluster
	@helm upgrade --install dt ./infra


.PHONY: uninstall
uninstall: ## Uninstall helm chart
	@helm uninstall dt


##@ Dev
.PHONY: traefik nodered mongo-express

