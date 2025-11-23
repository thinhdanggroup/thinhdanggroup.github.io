#!/usr/bin/env python3
"""
Dev.to Blog Post Publisher

This script publishes blog posts from your Jekyll blog to dev.to.
It converts Jekyll front matter to dev.to format and uses the dev.to API.

Requirements:
- Dev.to API key (get from: https://dev.to/settings/extensions)
- Python 3.7+

Usage:
    # Publish a specific post
    python publish_to_devto.py --post 2023-07-20-prompt-engineering

    # Publish recent N posts as drafts
    python publish_to_devto.py --recent 5 --draft

    # Publish all posts as drafts
    python publish_to_devto.py --all --draft

    # Dry run (show what would be published without actually publishing)
    python publish_to_devto.py --all --dry-run
"""

import os
import sys
import json
import argparse
import logging
import re
import yaml
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
POSTS_DIR = PROJECT_ROOT / "_posts"
CONFIG_FILE = SCRIPT_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://thinhdanggroup.github.io",
    "organization_id": None,  # Optional: organization to publish under
    "default_series": None,  # Optional: default series name
    "canonical_url_template": "https://thinhdanggroup.github.io/{slug}/",
}

# Dev.to API endpoints
DEVTO_API_URL = "https://dev.to/api/articles"
DEVTO_IMAGE_URL = "https://dev.to/api/images"


class DevToPublisher:
    def __init__(self, config_path: str = None, dry_run: bool = False):
        self.config = self._load_config(config_path)
        self.dry_run = dry_run
        self.logger = self._setup_logging()
        self.headers = {
            "api-key": self.config.get("api_key", ""),
            "Content-Type": "application/json",
        }

    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from file or use defaults."""
        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                config = json.load(f)
        elif CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        else:
            config = DEFAULT_CONFIG.copy()

        # Ensure all required keys exist
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value

        return config

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("devto_publisher")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _extract_front_matter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Extract YAML front matter from markdown content."""
        front_matter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(front_matter_pattern, content, re.DOTALL)

        if match:
            try:
                front_matter = yaml.safe_load(match.group(1))
                markdown_content = match.group(2)
                return front_matter, markdown_content
            except yaml.YAMLError as e:
                self.logger.error(f"Error parsing YAML front matter: {e}")
                return {}, content
        return {}, content

    def _upload_image_to_devto(self, image_path: str) -> Optional[str]:
        """Upload an image to dev.to and return the CDN URL."""
        try:
            # Check if image exists
            if not Path(image_path).exists():
                self.logger.warning(f"Image not found: {image_path}")
                return None

            # Read the image file
            with open(image_path, 'rb') as f:
                # Dev.to expects multipart/form-data with 'image' field
                files = {'image': (Path(image_path).name, f, 'image/png')}

                self.logger.info(f"Uploading image to dev.to: {Path(image_path).name}")
                response = requests.post(
                    DEVTO_IMAGE_URL,
                    headers={"api-key": self.config.get("api_key", "")},
                    files=files,
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    result = response.json()
                    # Try different possible response formats
                    devto_url = result.get('url') or result.get('image', {}).get('url')
                    if devto_url:
                        self.logger.info(f"✓ Image uploaded successfully: {devto_url}")
                        return devto_url
                    else:
                        self.logger.error(f"No URL in response: {result}")
                        return None
                else:
                    self.logger.warning(f"Image upload returned {response.status_code}, using fallback")
                    self.logger.debug(f"Response: {response.text[:200]}")
                    return None

        except Exception as e:
            self.logger.error(f"Error uploading image: {e}")
            return None

    def _convert_image_paths(self, content: str, base_url: str, upload_images: bool = False) -> str:
        """Convert relative image paths to absolute URLs or upload to dev.to."""
        # Pattern to match markdown images: ![alt](/path/to/image.png)
        image_pattern = r"!\[(.*?)\]\((/assets/.*?)\)"

        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)

            if upload_images and not self.dry_run:
                # Try to upload to dev.to
                local_path = PROJECT_ROOT / image_path.lstrip('/')
                devto_url = self._upload_image_to_devto(local_path)
                if devto_url:
                    return f"![{alt_text}]({devto_url})"

            # Fallback to absolute URL
            full_url = f"{base_url}{image_path}"
            return f"![{alt_text}]({full_url})"

        return re.sub(image_pattern, replace_image, content)

    def _get_slug_from_filename(self, filename: str) -> str:
        """Extract slug from filename (remove date prefix)."""
        # Remove date prefix (YYYY-MM-DD-) and .md extension
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", filename)
        slug = slug.replace(".md", "")
        return slug

    def _prepare_article(
        self, post_file: Path, published: bool = False, upload_images: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Prepare article data for dev.to API."""
        try:
            with open(post_file, "r", encoding="utf-8") as f:
                content = f.read()

            front_matter, markdown_content = self._extract_front_matter(content)

            if not front_matter:
                self.logger.warning(f"No front matter found in {post_file.name}")
                return None

            # Get title
            title = front_matter.get("title")
            if not title:
                self.logger.warning(f"No title found in {post_file.name}")
                return None

            # Get tags (dev.to supports up to 4 tags)
            tags = front_matter.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            # Limit to 4 tags and clean them
            tags = [str(tag).strip().lower().replace(" ", "") for tag in tags[:4]]

            # Get canonical URL
            slug = self._get_slug_from_filename(post_file.name)
            canonical_url = self.config["canonical_url_template"].format(slug=slug)

            # Convert image paths (upload to dev.to if enabled)
            markdown_content = self._convert_image_paths(
                markdown_content, self.config["base_url"], upload_images=upload_images
            )

            # Add footer with reference back to original blog
            footer = f"\n\n---\n\n*This article was originally published on [ThinhDangGroup Blog]({canonical_url})*\n"
            markdown_content = markdown_content.strip() + footer

            # Prepare article data
            article = {
                "article": {
                    "title": title,
                    "published": published,
                    "body_markdown": markdown_content,
                    "tags": tags,
                    "canonical_url": canonical_url,
                }
            }

            # Add optional fields
            if self.config.get("organization_id"):
                article["article"]["organization_id"] = self.config["organization_id"]

            if self.config.get("default_series") or front_matter.get("series"):
                series = front_matter.get("series", self.config.get("default_series"))
                if series:
                    article["article"]["series"] = series

            # Add main_image/cover image if available
            # Try multiple possible locations for banner/cover image
            main_image = None
            header = front_matter.get("header", {})

            # Priority: overlay_image > teaser > image
            if isinstance(header, dict):
                main_image = (
                    header.get("overlay_image")
                    or header.get("teaser")
                    or header.get("image")
                )

            # Also check for direct image field in front matter
            if not main_image:
                main_image = front_matter.get("image")

            # Handle the banner image
            if main_image:
                image_url = None

                # If it's a relative path and we should upload images
                if main_image.startswith("/") and upload_images and not self.dry_run:
                    # Try to upload to dev.to
                    local_path = PROJECT_ROOT / main_image.lstrip('/')
                    devto_url = self._upload_image_to_devto(local_path)
                    if devto_url:
                        image_url = devto_url
                        self.logger.info(f"Using dev.to CDN URL for banner")

                # Fallback to absolute URL if upload failed or disabled
                if not image_url:
                    if main_image.startswith("/"):
                        image_url = f"{self.config['base_url']}{main_image}"
                    elif main_image.startswith("http"):
                        image_url = main_image
                    else:
                        # Assume it's in assets
                        image_url = f"{self.config['base_url']}/{main_image}"

                    # Log the URL being used
                    self.logger.info(f"Using absolute URL for banner: {image_url}")

                # Set both main_image and cover_image to be safe
                # Different dev.to API versions may use different field names
                article["article"]["main_image"] = image_url
                article["article"]["cover_image"] = image_url

            # Add description if available
            if front_matter.get("excerpt"):
                article["article"]["description"] = front_matter["excerpt"]

            return article

        except Exception as e:
            self.logger.error(f"Error preparing article {post_file.name}: {e}")
            return None

    def publish_article(self, article_data: Dict[str, Any], post_name: str) -> bool:
        """Publish article to dev.to."""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would publish: {post_name}")
            self.logger.info(f"Title: {article_data['article']['title']}")
            self.logger.info(f"Tags: {article_data['article']['tags']}")
            self.logger.info(
                f"Published: {article_data['article'].get('published', False)}"
            )
            self.logger.info(
                f"Canonical URL: {article_data['article']['canonical_url']}"
            )
            if article_data["article"].get("main_image"):
                self.logger.info(
                    f"Cover Image: {article_data['article']['main_image']}"
                )
            else:
                self.logger.warning("⚠️  No cover image found!")
            self.logger.info(f"✓ Footer with blog reference added")

            # Show full article data for debugging
            self.logger.info("\n--- Full Article Data (for debugging) ---")
            self.logger.info(json.dumps(article_data, indent=2))
            self.logger.info("--- End Article Data ---\n")
            return True

        try:
            response = requests.post(
                DEVTO_API_URL, headers=self.headers, json=article_data, timeout=30
            )

            if response.status_code == 201:
                result = response.json()
                self.logger.info(
                    f"✓ Successfully published: {post_name} - {result.get('url', '')}"
                )
                return True
            elif response.status_code == 401:
                self.logger.error(
                    "Authentication failed. Please check your API key in config.json"
                )
                return False
            elif response.status_code == 422:
                error_msg = response.json()
                self.logger.error(f"Validation error for {post_name}: {error_msg}")
                return False
            else:
                self.logger.error(
                    f"Failed to publish {post_name}: {response.status_code} - {response.text}"
                )
                return False

        except requests.RequestException as e:
            self.logger.error(f"Network error publishing {post_name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error publishing {post_name}: {e}")
            return False

    def get_post_files(
        self, post_name: str = None, recent: int = None, all_posts: bool = False
    ) -> List[Path]:
        """Get list of post files to publish."""
        if not POSTS_DIR.exists():
            self.logger.error(f"Posts directory not found: {POSTS_DIR}")
            return []

        if post_name:
            # Single post
            post_file = POSTS_DIR / f"{post_name}.md"
            if post_file.exists():
                return [post_file]
            else:
                self.logger.error(f"Post not found: {post_file}")
                return []

        # Get all markdown files
        all_post_files = sorted(POSTS_DIR.glob("*.md"), reverse=True)

        if recent:
            # Return N most recent posts
            return all_post_files[:recent]
        elif all_posts:
            # Return all posts
            return all_post_files
        else:
            return []

    def publish(
        self,
        post_name: str = None,
        recent: int = None,
        all_posts: bool = False,
        published: bool = False,
        upload_images: bool = True,
    ):
        """Main publish method."""
        if not self.config.get("api_key") and not self.dry_run:
            self.logger.error(
                "API key not configured. Please set it in config.json or use --dry-run"
            )
            return

        post_files = self.get_post_files(post_name, recent, all_posts)

        if not post_files:
            self.logger.warning("No posts to publish")
            return

        self.logger.info(f"Found {len(post_files)} post(s) to publish")
        if upload_images and not self.dry_run:
            self.logger.info("Images will be uploaded to dev.to CDN")

        success_count = 0
        failed_count = 0

        for post_file in post_files:
            self.logger.info(f"\nProcessing: {post_file.name}")

            article_data = self._prepare_article(
                post_file, published=published, upload_images=upload_images
            )
            if not article_data:
                self.logger.warning(f"Skipping {post_file.name}")
                failed_count += 1
                continue

            if self.publish_article(article_data, post_file.name):
                success_count += 1
            else:
                failed_count += 1

        # Summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Publishing complete!")
        self.logger.info(f"Successfully published: {success_count}")
        self.logger.info(f"Failed: {failed_count}")
        self.logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Publish blog posts to dev.to",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Publish a specific post:
    python publish_to_devto.py --post 2023-07-20-prompt-engineering

  Publish 5 most recent posts as drafts:
    python publish_to_devto.py --recent 5 --draft

  Publish all posts as published articles:
    python publish_to_devto.py --all

  Dry run (test without publishing):
    python publish_to_devto.py --all --dry-run
        """,
    )

    # Mutually exclusive group for post selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--post", help="Specific post filename (without .md extension)")
    group.add_argument("--recent", type=int, help="Number of recent posts to publish")
    group.add_argument("--all", action="store_true", help="Publish all posts")

    # Publishing options
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Publish as draft (default is published)",
        default=False,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without actually publishing",
        default=False,
    )
    parser.add_argument(
        "--no-upload-images",
        action="store_true",
        help="Don't upload images to dev.to (use absolute URLs instead)",
        default=False,
    )
    parser.add_argument("--config", help="Path to config file")

    args = parser.parse_args()

    # Create publisher
    publisher = DevToPublisher(config_path=args.config, dry_run=args.dry_run)

    # Publish posts
    publisher.publish(
        post_name=args.post,
        recent=args.recent,
        all_posts=args.all,
        published=not args.draft,
        upload_images=not args.no_upload_images,
    )


if __name__ == "__main__":
    main()
