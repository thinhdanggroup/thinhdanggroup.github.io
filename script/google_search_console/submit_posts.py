#!/usr/bin/env python3
"""
Google Search Console URL Submission Script

This script automatically submits new blog posts to Google Search Console
for indexing. It can detect new posts based on modification time or git changes.

Requirements:
- Google Search Console API enabled in Google Cloud Console
- Service account credentials or OAuth2 credentials
- Website verified in Google Search Console

Usage:
    python submit_posts.py --mode recent --days 7
    python submit_posts.py --mode git --since HEAD~5
    python submit_posts.py --url "https://thinhdanggroup.github.io/specific-post/"
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import subprocess
import yaml

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import requests
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print(
        "Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests pyyaml"
    )
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
POSTS_DIR = PROJECT_ROOT / "_posts"
CONFIG_FILE = SCRIPT_DIR / "config.json"
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"

# Google Search Console API scopes
SCOPES = ["https://www.googleapis.com/auth/webmasters"]

# Default configuration
DEFAULT_CONFIG = {
    "site_url": "https://thinhdanggroup.github.io/",
    "base_url": "https://thinhdanggroup.github.io",
    "posts_pattern": "*.md",
    "excluded_files": ["README.md", "index.md"],
    "rate_limit_delay": 1.0,  # seconds between requests
    "max_urls_per_batch": 10,
    "oauth_port": 0,  # Use 0 for automatic port selection
    "oauth_host": "localhost",
}


class GoogleSearchConsoleSubmitter:
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.service = None
        self.logger = self._setup_logging()

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
        logger = logging.getLogger("gsc_submitter")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def authenticate(self) -> None:
        """Authenticate with Google Search Console API."""
        creds = None

        # Check for existing token
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {CREDENTIALS_FILE}\n"
                        "Please download OAuth2 credentials from Google Cloud Console"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )

                # Try local server first, fallback to console flow if it fails
                try:
                    # Use specific ports that are commonly allowed
                    for port in [8080, 8081, 9090, 0]:
                        try:
                            self.logger.info(
                                f"Attempting OAuth on port {port if port != 0 else 'auto'}"
                            )
                            creds = flow.run_local_server(
                                host="localhost",
                                port=port,
                                open_browser=True,
                                success_message="Authentication successful! You can close this window.",
                            )
                            break
                        except Exception as e:
                            if port == 0:  # Last attempt failed
                                raise e
                            self.logger.warning(f"Port {port} failed, trying next...")
                            continue
                except Exception as e:
                    self.logger.warning(f"Local server authentication failed: {e}")
                    self.logger.info("Falling back to console authentication...")

                    # Fallback to console-based authentication
                    creds = flow.run_console()

            # Save the credentials for the next run
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        self.service = build("searchconsole", "v1", credentials=creds)
        self.logger.info("Successfully authenticated with Google Search Console API")

    def get_recent_posts(self, days: int = 7) -> List[Path]:
        """Get posts modified within the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_posts = []

        for post_file in POSTS_DIR.glob(self.config["posts_pattern"]):
            if post_file.name in self.config["excluded_files"]:
                continue

            mod_time = datetime.fromtimestamp(post_file.stat().st_mtime)
            if mod_time > cutoff_date:
                recent_posts.append(post_file)

        self.logger.info(
            f"Found {len(recent_posts)} posts modified in last {days} days"
        )
        return recent_posts

    def get_git_changed_posts(self, since: str = "HEAD~1") -> List[Path]:
        """Get posts that have changed in git since a specific commit."""
        try:
            # Get changed files from git
            result = subprocess.run(
                ["git", "diff", "--name-only", since, "HEAD"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            changed_files = result.stdout.strip().split("\n")
            changed_posts = []

            for file_path in changed_files:
                if file_path.startswith("_posts/") and file_path.endswith(".md"):
                    post_file = PROJECT_ROOT / file_path
                    if (
                        post_file.exists()
                        and post_file.name not in self.config["excluded_files"]
                    ):
                        changed_posts.append(post_file)

            self.logger.info(f"Found {len(changed_posts)} posts changed since {since}")
            return changed_posts

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e}")
            return []

    def extract_post_metadata(self, post_file: Path) -> dict:
        """Extract metadata from Jekyll post front matter."""
        try:
            with open(post_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract front matter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    front_matter = yaml.safe_load(parts[1])
                    return front_matter or {}

            return {}

        except Exception as e:
            self.logger.warning(f"Could not parse front matter for {post_file}: {e}")
            return {}

    def post_file_to_url(self, post_file: Path) -> str:
        """Convert post file path to URL."""
        # Extract date and title from filename (YYYY-MM-DD-title.md)
        filename = post_file.stem

        # Try to parse Jekyll filename format
        parts = filename.split("-", 3)
        if len(parts) >= 4:
            year, month, day, title = parts[0], parts[1], parts[2], parts[3]
            # Jekyll permalink format from _config.yml: /:categories/:title/
            url = f"{self.config['base_url']}/{title}/"
        else:
            # Fallback to simple title-based URL
            title = filename.replace("-", "-")
            url = f"{self.config['base_url']}/{title}/"

        return url

    def submit_url(self, url: str) -> bool:
        """Submit a single URL to Google Search Console for indexing using URL Inspection API."""
        try:
            # Use the URL inspection API to inspect the URL
            request_body = {"inspectionUrl": url, "siteUrl": self.config["site_url"]}

            # First, inspect the URL to get its current status
            response = (
                self.service.urlInspection()
                .index()
                .inspect(body=request_body)
                .execute()
            )

            self.logger.info(f"URL inspection completed for: {url}")

            # Check if the URL can be indexed
            inspection_result = response.get("inspectionResult", {})
            index_status = inspection_result.get("indexStatusResult", {})

            if index_status.get("verdict") == "PASS":
                self.logger.info(f"URL is indexable: {url}")

                # Try to request indexing (this may not be available for all accounts)
                try:
                    index_response = (
                        self.service.urlInspection()
                        .index()
                        .request(body=request_body)
                        .execute()
                    )
                    self.logger.info(f"Indexing requested for URL: {url}")
                    return True
                except HttpError as index_error:
                    if index_error.resp.status == 403:
                        self.logger.warning(
                            f"Indexing request not available for this account. URL inspected: {url}"
                        )
                        return True  # Consider inspection as success
                    else:
                        raise index_error
            else:
                coverage_state = index_status.get("coverageState", "Unknown")
                self.logger.warning(
                    f"URL may not be indexable: {url} (Status: {coverage_state})"
                )
                return False

        except HttpError as e:
            error_details = e.error_details[0] if e.error_details else {}
            error_reason = error_details.get("reason", "Unknown error")

            if e.resp.status == 429:
                self.logger.warning(f"Rate limit exceeded for URL: {url}")
            elif e.resp.status == 403:
                self.logger.error(
                    f"Permission denied for URL: {url}. Check site verification and API permissions."
                )
            elif e.resp.status == 400:
                self.logger.error(f"Invalid URL or site URL: {url}")
            else:
                self.logger.error(f"Failed to process URL {url}: {error_reason}")

            return False

        except Exception as e:
            self.logger.error(f"Unexpected error processing URL {url}: {e}")
            return False

    def submit_urls_batch(self, urls: List[str]) -> dict:
        """Submit multiple URLs with rate limiting."""
        import time

        results = {"success": [], "failed": []}

        for i, url in enumerate(urls):
            if i > 0:
                time.sleep(self.config["rate_limit_delay"])

            if self.submit_url(url):
                results["success"].append(url)
            else:
                results["failed"].append(url)

        return results

    def submit_posts(self, post_files: List[Path]) -> dict:
        """Submit multiple posts to Google Search Console."""
        if not post_files:
            self.logger.info("No posts to submit")
            return {"success": [], "failed": []}

        # Convert post files to URLs
        urls = []
        for post_file in post_files:
            url = self.post_file_to_url(post_file)
            urls.append(url)
            self.logger.info(f"Prepared URL: {url} (from {post_file.name})")

        # Submit URLs in batches
        all_results = {"success": [], "failed": []}
        batch_size = self.config["max_urls_per_batch"]

        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            self.logger.info(
                f"Submitting batch {i//batch_size + 1} ({len(batch)} URLs)"
            )

            batch_results = self.submit_urls_batch(batch)
            all_results["success"].extend(batch_results["success"])
            all_results["failed"].extend(batch_results["failed"])

        return all_results


def create_config_file():
    """Create a default configuration file."""
    if not CONFIG_FILE.parent.exists():
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)

    print(f"Created default configuration file: {CONFIG_FILE}")
    print("Please review and update the configuration as needed.")


def main():
    parser = argparse.ArgumentParser(
        description="Submit blog posts to Google Search Console for indexing"
    )

    parser.add_argument(
        "--mode",
        choices=["recent", "git", "url"],
        default="recent",
        help="Mode for finding posts to submit",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for recent posts (default: 7)",
    )

    parser.add_argument(
        "--since",
        default="HEAD~1",
        help="Git commit reference to compare against (default: HEAD~1)",
    )

    parser.add_argument("--url", help="Specific URL to submit (use with --mode url)")

    parser.add_argument("--config", help="Path to configuration file")

    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be submitted without actually submitting",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.create_config:
        create_config_file()
        return

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize submitter
        submitter = GoogleSearchConsoleSubmitter(args.config)

        # Authenticate (skip in dry-run mode)
        if not args.dry_run:
            submitter.authenticate()

        # Get posts based on mode
        if args.mode == "recent":
            posts = submitter.get_recent_posts(args.days)
        elif args.mode == "git":
            posts = submitter.get_git_changed_posts(args.since)
        elif args.mode == "url":
            if not args.url:
                print("Error: --url is required when using --mode url")
                sys.exit(1)

            if args.dry_run:
                print(f"Would submit URL: {args.url}")
                return
            else:
                success = submitter.submit_url(args.url)
                print(f"URL submission {'successful' if success else 'failed'}")
                return
        else:
            print(f"Unknown mode: {args.mode}")
            sys.exit(1)

        if not posts:
            print("No posts found to submit")
            return

        # Show what will be submitted
        print(f"Found {len(posts)} posts to submit:")
        for post in posts:
            url = submitter.post_file_to_url(post)
            print(f"  - {post.name} -> {url}")

        if args.dry_run:
            print("\nDry run mode - no URLs were actually submitted")
            return

        # Submit posts
        print(f"\nSubmitting {len(posts)} posts to Google Search Console...")
        results = submitter.submit_posts(posts)

        # Report results
        print(f"\nSubmission complete:")
        print(f"  Success: {len(results['success'])}")
        print(f"  Failed: {len(results['failed'])}")

        if results["failed"]:
            print("\nFailed URLs:")
            for url in results["failed"]:
                print(f"  - {url}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
