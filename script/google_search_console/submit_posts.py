#!/usr/bin/env python3
"""
Google Search Console URL Inspection Script

This script automatically inspects new blog posts using Google Search Console's
URL Inspection API. It provides detailed indexing status and helps identify
potential issues. Note: Google has deprecated the programmatic indexing request
API, so this script focuses on inspection and monitoring.

Requirements:
- Google Search Console API enabled in Google Cloud Console
- OAuth2 credentials (Desktop Application)
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
from typing import List, Optional, Dict
import subprocess
import yaml
import csv

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

    def inspect_url(self, url: str) -> Dict:
        """Inspect a single URL using Google Search Console URL Inspection API."""
        result = {
            "url": url,
            "success": False,
            "coverage_state": "Unknown",
            "verdict": "Unknown",
            "fetch_state": "Unknown",
            "last_crawl_time": "Unknown",
            "indexing_allowed": "Unknown",
            "user_canonical": "Unknown",
            "google_canonical": "Unknown",
            "error": None,
        }

        try:
            # Use the URL inspection API to inspect the URL
            request_body = {
                "inspectionUrl": url,
                "siteUrl": self.config["site_url"],
                "languageCode": "en-US",
            }

            # Inspect the URL to get its current status
            self.logger.info(f"Inspecting URL: {url}")
            response = (
                self.service.urlInspection()
                .index()
                .inspect(body=request_body)
                .execute()
            )

            # Extract inspection results
            inspection_result = response.get("inspectionResult", {})
            index_status = inspection_result.get("indexStatusResult", {})

            # Basic status information
            result["coverage_state"] = index_status.get("coverageState", "Unknown")
            result["verdict"] = index_status.get("verdict", "Unknown")
            result["indexing_allowed"] = index_status.get("robotsTxtState", "Unknown")
            result["user_canonical"] = index_status.get("userCanonical", "Unknown")
            result["google_canonical"] = index_status.get("googleCanonical", "Unknown")

            # Crawl information
            crawl_result = inspection_result.get("pageFetchResult", {})
            if crawl_result:
                result["fetch_state"] = crawl_result.get("fetchState", "Unknown")

            # Last crawl time
            if "lastCrawlTime" in index_status:
                result["last_crawl_time"] = index_status["lastCrawlTime"]

            result["success"] = True

            # Log the inspection results
            self.logger.info(
                f"URL {url} - Coverage: {result['coverage_state']}, Verdict: {result['verdict']}"
            )

            return result

        except HttpError as e:
            error_details = e.error_details[0] if e.error_details else {}
            error_reason = error_details.get("reason", "Unknown error")

            result["error"] = f"HTTP {e.resp.status}: {error_reason}"

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

            return result

        except Exception as e:
            self.logger.error(f"Unexpected error processing URL {url}: {e}")
            result["error"] = str(e)
            return result

    def submit_url(self, url: str) -> bool:
        """Legacy method for backward compatibility."""
        result = self.inspect_url(url)
        return result["success"]

    def inspect_urls_batch(self, urls: List[str]) -> List[Dict]:
        """Inspect multiple URLs with rate limiting and return detailed results."""
        import time

        results = []

        for i, url in enumerate(urls):
            if i > 0:
                time.sleep(self.config["rate_limit_delay"])

            result = self.inspect_url(url)
            results.append(result)

        return results

    def submit_urls_batch(self, urls: List[str]) -> dict:
        """Legacy method for backward compatibility."""
        results = {"success": [], "failed": []}
        inspection_results = self.inspect_urls_batch(urls)

        for result in inspection_results:
            if result["success"]:
                results["success"].append(result["url"])
            else:
                results["failed"].append(result["url"])

        return results

    def export_to_csv(
        self, inspection_results: List[Dict], filename: str = None
    ) -> str:
        """Export inspection results to CSV file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gsc_inspection_results_{timestamp}.csv"

        filepath = SCRIPT_DIR / filename

        # Define CSV headers
        headers = [
            "url",
            "success",
            "coverage_state",
            "verdict",
            "fetch_state",
            "last_crawl_time",
            "indexing_allowed",
            "user_canonical",
            "google_canonical",
            "error",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(inspection_results)

        self.logger.info(f"Exported {len(inspection_results)} results to {filepath}")
        return str(filepath)

    def filter_not_submitted_but_indexable(
        self, inspection_results: List[Dict]
    ) -> List[Dict]:
        """Filter URLs that are not 'Submitted and indexed' but have 'Verdict: PASS'."""
        filtered = []

        for result in inspection_results:
            if (
                result["success"]
                and result["verdict"] == "PASS"
                and result["coverage_state"] != "Submitted and indexed"
            ):
                filtered.append(result)

        return filtered

    def inspect_posts(self, post_files: List[Path]) -> List[Dict]:
        """Inspect multiple posts and return detailed results."""
        if not post_files:
            self.logger.info("No posts to inspect")
            return []

        # Convert post files to URLs
        urls = []
        for post_file in post_files:
            url = self.post_file_to_url(post_file)
            urls.append(url)
            self.logger.info(f"Prepared URL: {url} (from {post_file.name})")

        # Inspect URLs in batches
        all_results = []
        batch_size = self.config["max_urls_per_batch"]

        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            self.logger.info(
                f"Inspecting batch {i//batch_size + 1} ({len(batch)} URLs)"
            )

            batch_results = self.inspect_urls_batch(batch)
            all_results.extend(batch_results)

        return all_results

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

    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export detailed inspection results to CSV file",
    )

    parser.add_argument(
        "--csv-filename",
        help="Custom filename for CSV export (default: auto-generated with timestamp)",
    )

    parser.add_argument(
        "--filter-not-submitted",
        action="store_true",
        help="Export only URLs that are not 'Submitted and indexed' but have 'Verdict: PASS'",
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

        # Show what will be inspected
        print(f"Found {len(posts)} posts to inspect:")
        for post in posts:
            url = submitter.post_file_to_url(post)
            print(f"  - {post.name} -> {url}")

        if args.dry_run:
            print("\nDry run mode - no URLs were actually inspected")
            return

        # Inspect posts
        print(f"\nInspecting {len(posts)} posts using Google Search Console...")
        inspection_results = submitter.inspect_posts(posts)

        # Filter results if requested
        if args.filter_not_submitted:
            filtered_results = submitter.filter_not_submitted_but_indexable(
                inspection_results
            )
            print(
                f"\nFiltered results: {len(filtered_results)} URLs are indexable but not submitted"
            )
            results_to_export = filtered_results
        else:
            results_to_export = inspection_results

        # Export to CSV if requested
        if args.export_csv and results_to_export:
            csv_file = submitter.export_to_csv(results_to_export, args.csv_filename)
            print(f"\nResults exported to: {csv_file}")

        # Report summary
        success_count = sum(1 for r in inspection_results if r["success"])
        failed_count = len(inspection_results) - success_count

        print(f"\nInspection complete:")
        print(f"  Successfully inspected: {success_count}")
        print(f"  Failed: {failed_count}")

        # Show summary of coverage states
        coverage_summary = {}
        verdict_summary = {}

        for result in inspection_results:
            if result["success"]:
                coverage = result["coverage_state"]
                verdict = result["verdict"]

                coverage_summary[coverage] = coverage_summary.get(coverage, 0) + 1
                verdict_summary[verdict] = verdict_summary.get(verdict, 0) + 1

        if coverage_summary:
            print(f"\nCoverage State Summary:")
            for state, count in coverage_summary.items():
                print(f"  {state}: {count}")

        if verdict_summary:
            print(f"\nVerdict Summary:")
            for verdict, count in verdict_summary.items():
                print(f"  {verdict}: {count}")

        # Show URLs that need attention
        if args.filter_not_submitted:
            if results_to_export:
                print(f"\nURLs that are indexable but not submitted:")
                for result in results_to_export:
                    print(f"  - {result['url']} (Coverage: {result['coverage_state']})")
            else:
                print(f"\nAll indexable URLs are already submitted and indexed!")

        # Show failed URLs
        failed_results = [r for r in inspection_results if not r["success"]]
        if failed_results:
            print("\nFailed inspections:")
            for result in failed_results:
                print(f"  - {result['url']}: {result['error']}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
