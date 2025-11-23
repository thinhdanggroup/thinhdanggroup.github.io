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
