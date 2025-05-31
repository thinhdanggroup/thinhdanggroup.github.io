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
