default: install

all: install build


h help:
	@grep '^[a-z]' Makefile


install:
	bundle config set --local path vendor/bundle
	bundle install

optimize-images:
	./script/optimize-images/optimize-images.sh

upgrade:
	bundle update


s serve:
	bundle exec jekyll serve --trace --livereload

indexnow:
	python script/indexnow/main.py
