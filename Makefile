#!make
SHELL := /bin/bash
.ONESHELL:

include docker/vars.env
include devtools.mk

PROJECT_DIR := $(PWD)
PROJECT_NAME := $(shell basename "$(PWD)" | tr '[:upper:]' '[:lower:]')
JUPYTER_TOKEN := $(shell openssl rand -hex 16)

# For Mac
HOST_UID ?= 1000
HOST_GID ?= 1000

# For linux
# HOST_UID ?= $(strip $(if $(shell id -u),$(shell id -u),4000))
# HOST_GID ?= $(strip $(if $(shell id -g),$(shell id -g),4444))



# -----------------------------------------------------------
# LIST MAKE TARGETS
# -----------------------------------------------------------
.PHONY: help ## to print available make targets
help:
	@echo "LIST OF AVAILABLE MAKE TARGETS:"
	@echo
	@grep -E '^\.PHONY: [a-zA-Z.-]+' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = "(: |##)"}; {printf "\033[33m%-25s\033[37m %s\n", $$2, $$3}'

# -----------------------------------------------------------
# ENVIRONMENT VARIABLES SETUP
# -----------------------------------------------------------
.PHONY: .env ## to export environment variables for docker compose
.env:
	cat docker/vars.env > docker/.env
	echo "" >>  docker/.env
	echo "PROJECT_DIR=${PROJECT_DIR}" >> docker/.env
	echo "PROJECT_NAME=${PROJECT_NAME}" >> docker/.env
	echo "HOST_UID=${HOST_UID}" >> docker/.env
	echo "HOST_GID=${HOST_GID}" >> docker/.env
	@ echo "JUPYTER_TOKEN=$(JUPYTER_TOKEN)" >> docker/.env

# -----------------------------------------------------------
# DOCKER CONTAINERS
# -----------------------------------------------------------
.PHONY: init ## to build docker images, start containers and install dev dependencies
init: stop build start install-dev
	@echo "Initilization of local environment is complete."

.PHONY: clean ## to remove containers, attached volumes and networks
clean:
	docker compose -f docker/docker-compose.yaml -p $(PROJECT_NAME) down --remove-orphans

.PHONY: build ## to build images with docker compose
build: .env
	docker compose -f docker/docker-compose.yaml -p $(PROJECT_NAME) build

.PHONY: start-docker ## to start the containers
start: .env
	docker compose -f docker/docker-compose.yaml -p $(PROJECT_NAME) up -d

.PHONY: stop ## to stop the running containers
stop:
	- docker compose -f docker/docker-compose.yaml -p $(PROJECT_NAME) stop

.PHONY: shell ## to attach terminal to the running python container
shell:
	@docker exec -it $(PROJECT_NAME)-pythonenv /bin/sh -c "/entrypoint.sh bash"

.PHONY: root ## to attach terminal as root to the running python container
root:
	@docker exec -u root -it $(PROJECT_NAME)-pythonenv /bin/sh -c "/entrypoint.sh bash"

.PHONY: install-dev ## to install development dependencies in python container
install-dev:
	docker exec $(PROJECT_NAME)-pythonenv /bin/sh -c "uv sync --extra dev"


# -----------------------------------------------------------
# HOUSEKEEPING
# -----------------------------------------------------------
.PHONY: rm-cached ## to remove temporary and cached files
rm-cached:
	find . -name '__pycache__' -type d -exec rm -rf {} +
	find . -name '*.pyc' -type f -delete
	find . -name '.ipynb_checkpoints' -type d -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage