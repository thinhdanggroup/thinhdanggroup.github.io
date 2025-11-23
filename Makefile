default: install

all: install build


h help:
	@grep '^[a-z]' Makefile


install:
	bundle config set --local path vendor/bundle
	bundle install

upgrade:
	bundle update


serve:
	bundle exec jekyll serve --trace --livereload

build:
	bundle exec jekyll build

indexnow:
	python script/indexnow/main.py

# Google Search Console submission
gsc-setup:
	./script/google_search_console/submit.sh setup

gsc-recent:
	./script/google_search_console/submit.sh recent

gsc-git:
	./script/google_search_console/submit.sh git

gsc-test:
	./script/google_search_console/submit.sh test

gsc-csv:
	./script/google_search_console/submit.sh csv

gsc-csv-filter:
	python script/google_search_console/submit_posts.py --mode recent --days 30 --export-csv --filter-not-submitted

generate:
	python ./script/write_log/app.py
	python ./script/export_posts.py

# Submit to both IndexNow and Google Search Console
submit-all: indexnow gsc-recent

# Medium publishing
medium-install:
	pip install -r script/medium/requirements.txt

medium-post:
	python script/medium/publish_to_medium.py --post $(POST)

medium-recent:
	python script/medium/publish_to_medium.py --recent $(N) --draft

medium-all:
	python script/medium/publish_to_medium.py --all --draft

medium-dry-run:
	python script/medium/publish_to_medium.py --all --dry-run

medium-setup:
	@echo "Setting up Medium publisher..."
	@echo "1. Install dependencies: make medium-install"
	@echo "2. Copy config template: cp script/medium/config.json.template script/medium/config.json"
	@echo "3. Edit config.json with your Medium integration token"
	@echo "4. Get token from: https://medium.com/me/settings"

# Dev.to publishing
devto-install:
	pip install -r script/devto/requirements.txt

devto-post:
	python script/devto/publish_to_devto.py --post $(POST) --draft

devto-recent:
	python script/devto/publish_to_devto.py --recent $(N) --draft

devto-all:
	python script/devto/publish_to_devto.py --all --draft

devto-dry-run:
	python script/devto/publish_to_devto.py --all --dry-run

devto-setup:
	@echo "Setting up Dev.to publisher..."
	@echo "1. Install dependencies: make devto-install"
	@echo "2. Copy config template: cp script/devto/config.json.template script/devto/config.json"
	@echo "3. Edit config.json with your Dev.to API key"
	@echo "4. Get API key from: https://dev.to/settings/extensions"
	@echo "5. Test with dry-run: make devto-dry-run"

devto-optimize-image:
	@if [ -z "$(IMAGE)" ]; then \
		echo "Usage: make devto-optimize-image IMAGE=path/to/image.png"; \
		exit 1; \
	fi
	./script/devto/optimize_image.sh $(IMAGE)
