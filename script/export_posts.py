#!/usr/bin/env python3
"""
Script to read all blog posts from _posts directory and export their titles to JSON.
"""

import os
import json
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any


def extract_front_matter(content: str) -> Dict[str, Any]:
    """Extract YAML front matter from markdown content."""
    # Match front matter between --- delimiters
    front_matter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(front_matter_pattern, content, re.DOTALL)

    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            print(f"Error parsing YAML front matter: {e}")
            return {}
    return {}


def get_post_info(file_path: Path) -> Dict[str, str]:
    """Extract post information from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        front_matter = extract_front_matter(content)

        # Extract filename without extension for fallback
        filename = file_path.stem

        # Get title from front matter or use filename as fallback
        title = front_matter.get("title", filename)

        # Extract date from filename (YYYY-MM-DD format)
        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})-", filename)
        date = date_match.group(1) if date_match else "Unknown"

        # Get tags if available
        tags = front_matter.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        return {
            "filename": filename,
            "title": title,
            "date": date,
            "tags": tags,
            "file_path": str(file_path.relative_to(file_path.parent.parent)),
        }

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return {
            "filename": file_path.stem,
            "title": file_path.stem,
            "date": "Unknown",
            "tags": [],
            "file_path": str(file_path.relative_to(file_path.parent.parent)),
            "error": str(e),
        }


def main():
    """Main function to process all posts and export to JSON."""
    # Get the script directory and navigate to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    posts_dir = project_root / "_posts"

    if not posts_dir.exists():
        print(f"Posts directory not found: {posts_dir}")
        return

    print(f"Reading posts from: {posts_dir}")

    # Get all markdown files in _posts directory
    post_files = list(posts_dir.glob("*.md"))
    print(f"Found {len(post_files)} post files")

    # Extract information from each post
    posts_data = []
    for post_file in sorted(post_files):
        print(f"Processing: {post_file.name}")
        post_info = get_post_info(post_file)
        posts_data.append(post_info)

    # Sort posts by date (newest first)
    posts_data.sort(key=lambda x: x["date"], reverse=True)

    # Create output data structure
    output_data = {
        "total_posts": len(posts_data),
        "generated_at": str(Path.cwd()),
        "posts": posts_data,
    }

    # Export to JSON file in project root
    output_file = project_root / "blog_posts.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nSuccessfully exported {len(posts_data)} blog posts to: {output_file}")
        print(f"Total posts: {len(posts_data)}")

        # Print some sample titles
        print("\nSample blog post titles:")
        for i, post in enumerate(posts_data[:5]):
            print(f"  {i+1}. {post['title']} ({post['date']})")

        if len(posts_data) > 5:
            print(f"  ... and {len(posts_data) - 5} more posts")

    except Exception as e:
        print(f"Error writing JSON file: {e}")


if __name__ == "__main__":
    main()
