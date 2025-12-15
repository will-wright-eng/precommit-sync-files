#* Variables
REPO_ROOT := $(shell git rev-parse --show-toplevel)

# Extract version from __init__.py
VERSION := $(shell grep -E "^__version__ = " precommit_sync_files/__init__.py | cut -d'"' -f2)
TAG := v$(VERSION)

#* Setup
.PHONY: $(shell sed -n -e '/^$$/ { n ; /^[^ .\#][^ ]*:/ { s/:.*$$// ; p ; } ; }' $(MAKEFILE_LIST))
.DEFAULT_GOAL := help

help: ## list make commands
	@echo ${MAKEFILE_LIST}
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

tag-and-sync: tag sync ## tag and sync files

tag: ## tag the current commit with the version
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: Could not extract version from precommit_sync_files/__init__.py"; \
		exit 1; \
	fi
	@echo "Tagging current commit with $(TAG)"
	git tag $(TAG)
	@echo "Tag $(TAG) created successfully"

version: ## print the version
	@echo $(VERSION)
