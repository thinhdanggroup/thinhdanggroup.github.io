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

generate:
    python ./script/write_log/app.py
    python ./script/export_posts.py
