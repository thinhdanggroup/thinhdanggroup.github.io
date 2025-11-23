# Google Search Console URL Inspection Script

This script automatically inspects your new blog posts using Google Search Console's URL Inspection API. It provides detailed indexing status and helps identify potential issues with your posts. Note: Google has deprecated the programmatic indexing request API, so this script focuses on inspection and monitoring.

## Features

-   🔍 **Multiple Detection Modes**: Find new posts by recent changes, git commits, or inspect specific URLs
-   🚀 **Automatic URL Generation**: Converts Jekyll post files to proper URLs based on your site structure
-   ⚡ **Rate Limited**: Respects Google's API rate limits with configurable delays
-   🔐 **Secure Authentication**: Uses OAuth2 for secure API access
-   📊 **Detailed Inspection**: Provides indexing status, coverage state, and fetch results
-   📝 **Comprehensive Logging**: Detailed logging and error handling
-   🧪 **Dry Run Mode**: Test what would be inspected without actually making API calls

## Prerequisites

### 1. Google Cloud Console Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Search Console API**:
    - Navigate to "APIs & Services" > "Library"
    - Search for "Google Search Console API"
    - Click on it and press "Enable"

### 2. Create Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. If prompted, configure the OAuth consent screen first:
    - Choose "External" user type (unless you have a Google Workspace)
    - Fill in required fields (App name, User support email, Developer contact)
    - Add your email to test users if in testing mode
4. Choose "Desktop Application" as the application type
5. Name it something like "Blog GSC Submitter"
6. **Add Authorized Redirect URIs** (click "ADD URI" for each):
    - `http://localhost:8080/`
    - `http://localhost:8081/`
    - `http://localhost:9090/`
    - `http://localhost/` (for fallback)
7. Download the JSON file and save it as `credentials.json` in this directory

### 3. Verify Your Website

Make sure your website is verified in [Google Search Console](https://search.google.com/search-console/).

## Installation

1. **Install Python Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2. **Place Credentials**:

    - Download your OAuth2 credentials from Google Cloud Console
    - Save the file as `credentials.json` in this directory

3. **Configure the Script** (optional):
    - The script will create a default `config.json` on first run
    - Modify the configuration as needed for your site

## Usage

### Basic Usage

Submit posts modified in the last 7 days:

```bash
python submit_posts.py
```

Submit posts modified in the last 3 days:

```bash
python submit_posts.py --mode recent --days 3
```

### Git-Based Detection

Submit posts changed since the last commit:

```bash
python submit_posts.py --mode git
```

Submit posts changed since 5 commits ago:

```bash
python submit_posts.py --mode git --since HEAD~5
```

Submit posts changed since a specific commit:

```bash
python submit_posts.py --mode git --since abc1234
```

### Submit Specific URL

```bash
python submit_posts.py --mode url --url "https://thinhdanggroup.github.io/your-post-title/"
```

### Dry Run Mode

Test what would be submitted without actually submitting:

```bash
python submit_posts.py --dry-run
```

### Verbose Logging

Enable detailed logging:

```bash
python submit_posts.py --verbose
```

## Configuration

The script uses a `config.json` file for configuration. Here are the available options:

```json
{
    "site_url": "https://thinhdanggroup.github.io/",
    "base_url": "https://thinhdanggroup.github.io",
    "posts_pattern": "*.md",
    "excluded_files": ["README.md", "index.md"],
    "rate_limit_delay": 1.0,
    "max_urls_per_batch": 10
}
```

-   `site_url`: Your site URL as registered in Google Search Console
-   `base_url`: Base URL for generating post URLs
-   `posts_pattern`: Glob pattern to match post files
-   `excluded_files`: Files to exclude from submission
-   `rate_limit_delay`: Delay between API requests (seconds)
-   `max_urls_per_batch`: Maximum URLs to submit in one batch

## Authentication Flow

On first run, the script will:

1. Open your web browser
2. Ask you to sign in to your Google account
3. Request permission to access Search Console
4. Save authentication tokens for future use

The tokens are saved in `token.json` and will be automatically refreshed as needed.

## Examples

### Daily Automation

Add to your crontab to run daily:

```bash
# Submit new posts daily at 9 AM
0 9 * * * cd /path/to/script && python submit_posts.py --mode recent --days 1
```

### CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Submit new posts to Google Search Console
  run: |
      cd script/google_search_console
      python submit_posts.py --mode git --since ${{ github.event.before }}
  env:
      GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
```

### Post-Deployment Hook

Run after deploying new content:

```bash
# In your deployment script
python script/google_search_console/submit_posts.py --mode recent --days 1
```

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**

    - Make sure `credentials.json` exists in the script directory
    - Download OAuth2 credentials from Google Cloud Console

2. **"Permission denied"**

    - Verify your website in Google Search Console
    - Check that the site URL in config matches exactly

3. **"Rate limit exceeded"**

    - Increase `rate_limit_delay` in config.json
    - Reduce `max_urls_per_batch`

4. **"Invalid URL format"**

    - Check your Jekyll permalink configuration
    - Verify the URL generation logic matches your site structure

5. **OAuth/Redirect URI Issues**
    - Make sure you created a "Desktop Application" (not Web Application)
    - **Add all required redirect URIs** in Google Cloud Console:
        - `http://localhost:8080/`
        - `http://localhost:8081/`
        - `http://localhost:9090/`
        - `http://localhost/`
    - If you see "redirect_uri_mismatch", add the missing URI to your OAuth client
    - The script tries multiple ports and falls back to console auth if needed

### Debug Mode

Run with verbose logging to see detailed information:

```bash
python submit_posts.py --verbose --dry-run
```

## API Limits

-   Google Search Console API has daily quotas
-   The script includes rate limiting to avoid hitting limits
-   Monitor your API usage in Google Cloud Console

## Security Notes

-   Keep `credentials.json` and `token.json` secure
-   Add them to `.gitignore` to avoid committing to version control
-   Use service accounts for production environments

## Integration with Existing Scripts

This script complements your existing IndexNow script (`../indexnow/main.py`). You can run both:

1. **IndexNow**: For immediate notification to Bing and other search engines
2. **Google Search Console**: For Google-specific indexing

Consider running both scripts in sequence for maximum search engine coverage.
