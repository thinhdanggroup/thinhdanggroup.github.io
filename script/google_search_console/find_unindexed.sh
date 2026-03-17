#!/bin/bash
#
# Find Unindexed Pages
# This script checks all URLs in your sitemap and exports unindexed pages to CSV
#
# Usage:
#   ./find_unindexed.sh                    # Find unindexed pages, auto-generate CSV filename
#   ./find_unindexed.sh output.csv         # Specify custom CSV filename
#   ./find_unindexed.sh --all              # Export all pages (not just unindexed)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Google Search Console - Find Unindexed Pages${NC}\n"

# Check if Python script exists
if [ ! -f "submit_posts.py" ]; then
    echo -e "${RED}Error: submit_posts.py not found${NC}"
    exit 1
fi

# Parse arguments
FILTER_UNINDEXED="--filter-unindexed"
CSV_FILENAME=""

if [ "$1" == "--all" ]; then
    FILTER_UNINDEXED=""
    echo -e "${YELLOW}Mode: Exporting ALL pages${NC}"
else
    echo -e "${YELLOW}Mode: Finding unindexed pages only${NC}"
    if [ -n "$1" ]; then
        CSV_FILENAME="--csv-filename $1"
    fi
fi

# Run the inspection
echo -e "\n${GREEN}Fetching and inspecting URLs from sitemap...${NC}"
echo -e "${YELLOW}This may take a while depending on the number of URLs${NC}\n"

python3 submit_posts.py \
    --mode sitemap \
    $FILTER_UNINDEXED \
    $CSV_FILENAME

echo -e "\n${GREEN}✅ Done!${NC}"

