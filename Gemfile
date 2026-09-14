source "https://rubygems.org"

gem "github-pages", "~> 228"
# gem "minimal-mistakes-jekyll"
gem "jekyll", "~> 3.9.3"
gem "kramdown-parser-gfm"
gem "faraday-retry", require: false
gem "jekyll-seo-tag"
gem "jekyll-remote-theme"
group :jekyll_plugins do
    gem "jekyll-feed", "~> 0.12"
    gem 'jekyll-sitemap'
end

# Used by CI (and available locally) to validate the built site.
group :test do
  gem "html-proofer", "~> 5.0"
end
