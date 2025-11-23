#!/usr/bin/env python3
"""
Blog Creation Script

This script automates the creation of new blog posts by:
1. Taking a blog name as input
2. Copying blog.md to _posts with proper date formatting
3. Generating the header with correct paths
4. Copying banner.png to the appropriate assets folder
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def slugify(text):
    """Convert text to URL-friendly slug"""
    return text.lower().replace(" ", "-").replace("_", "-")


def get_blog_title_from_content(content):
    """Extract the first H1 title from markdown content"""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Blog Post"


def generate_header(blog_name, title, tags=None):
    """Generate the blog post header in YAML format"""
    if tags is None:
        tags = ["System Design"]

    tag_lines = "\n".join([f"    - {tag}" for tag in tags])

    header = f"""---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        - label: "Linkedin"
          icon: "fab fa-fw fa-linkedin"
          url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/{blog_name}/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/{blog_name}/banner.png
title: "{title}"
tags:
{tag_lines}
---

"""
    return header


def create_blog_post(blog_name_input, tags=None):
    """
    Main function to create a blog post

    Args:
        blog_name_input: The name/title of the blog (will be slugified)
        tags: Optional list of tags for the blog post
    """
    # Get current directory (script folder)
    script_dir = Path(__file__).parent.resolve()

    # Get workspace root (two levels up from script)
    workspace_root = script_dir.parent.parent

    # Paths
    blog_template = script_dir / "blog.md"
    banner_source = script_dir / "banner.png"
    posts_dir = workspace_root / "_posts"
    assets_dir = workspace_root / "assets" / "images"

    # Validate source files exist
    if not blog_template.exists():
        print(f"❌ Error: blog.md not found at {blog_template}")
        return False

    if not banner_source.exists():
        print(f"❌ Error: banner.png not found at {banner_source}")
        return False

    # Create slugified blog name
    blog_slug = slugify(blog_name_input)

    # Read the blog content to extract title
    with open(blog_template, "r", encoding="utf-8") as f:
        blog_content = f.read()

    # Update UTM source from chatgpt.com to thinhdanggroup.github.io
    blog_content = blog_content.replace(
        "utm_source=chatgpt.com", "utm_source=thinhdanggroup.github.io"
    )
    print("🔗 Updated UTM source links to thinhdanggroup.github.io")

    # Extract title from content
    blog_title = get_blog_title_from_content(blog_content)
    print(f"📝 Extracted title: {blog_title}")

    # Generate date-based filename
    current_date = datetime.now().strftime("%Y-%m-%d")
    post_filename = f"{current_date}-{blog_slug}.md"
    post_path = posts_dir / post_filename

    # Check if post already exists
    if post_path.exists():
        overwrite = input(f"⚠️  Post {post_filename} already exists. Overwrite? (y/n): ")
        if overwrite.lower() != "y":
            print("❌ Operation cancelled")
            return False

    # Create assets directory for this blog
    blog_assets_dir = assets_dir / blog_slug
    blog_assets_dir.mkdir(parents=True, exist_ok=True)

    # Copy banner
    banner_dest = blog_assets_dir / "banner.png"
    shutil.copy2(banner_source, banner_dest)
    print(f"✅ Banner copied to: {banner_dest}")

    # Generate header
    header = generate_header(blog_slug, blog_title, tags)

    # Write the new blog post
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(blog_content)

    print(f"✅ Blog post created: {post_path}")
    print(f"📁 Assets folder: {blog_assets_dir}")
    print(f"\n🎉 Done! Your blog post is ready at:")
    print(f"   {post_path}")

    return True


def main():
    """Main entry point"""
    print("=" * 60)
    print("Blog Post Creation Script")
    print("=" * 60)
    print()

    # Get blog name from user
    blog_name = input("Enter blog name (will be slugified): ").strip()

    if not blog_name:
        print("❌ Error: Blog name cannot be empty")
        return

    # Get tags (optional)
    tags_input = input(
        "Enter tags (comma-separated, or press Enter for default): "
    ).strip()
    tags = None
    if tags_input:
        tags = [tag.strip() for tag in tags_input.split(",")]

    print()
    print("-" * 60)
    print(f"Blog Name: {blog_name}")
    print(f"Slug: {slugify(blog_name)}")
    if tags:
        print(f"Tags: {', '.join(tags)}")
    print("-" * 60)
    print()

    # Confirm
    confirm = input("Proceed with creation? (y/n): ")
    if confirm.lower() != "y":
        print("❌ Operation cancelled")
        return

    print()
    # Create the blog post
    create_blog_post(blog_name, tags)


if __name__ == "__main__":
    main()
