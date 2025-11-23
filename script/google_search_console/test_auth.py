#!/usr/bin/env python3
"""
Simple test script to verify Google Search Console API authentication
"""

import os
import sys
from pathlib import Path

# Add the script directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/webmasters"]
CREDENTIALS_FILE = script_dir / "credentials.json"
TOKEN_FILE = script_dir / "token.json"


def test_authentication():
    """Test Google Search Console API authentication."""
    print("Testing Google Search Console API authentication...")

    if not CREDENTIALS_FILE.exists():
        print(f"Error: credentials.json not found at {CREDENTIALS_FILE}")
        print("Please download OAuth2 credentials from Google Cloud Console")
        return False

    creds = None

    # Check for existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("Starting OAuth flow...")
            print(
                "Make sure you have added http://localhost:8080/ as a redirect URI in Google Cloud Console"
            )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        print("Credentials saved successfully!")

    try:
        # Build the service
        service = build("searchconsole", "v1", credentials=creds)

        # Test by listing sites
        print("Testing API access by listing sites...")
        sites_response = service.sites().list().execute()

        sites = sites_response.get("siteEntry", [])
        if sites:
            print(f"✅ Authentication successful! Found {len(sites)} verified sites:")
            for site in sites:
                site_url = site.get("siteUrl", "Unknown")
                permission_level = site.get("permissionLevel", "Unknown")
                print(f"  - {site_url} (Permission: {permission_level})")
        else:
            print("⚠️  Authentication successful, but no verified sites found.")
            print("Please verify your website in Google Search Console first.")

        return True

    except HttpError as e:
        print(f"❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_authentication()
    if success:
        print("\n🎉 Authentication test completed successfully!")
        print("You can now use the main script to submit URLs.")
    else:
        print("\n❌ Authentication test failed.")
        print("Please check your credentials and try again.")
        sys.exit(1)
