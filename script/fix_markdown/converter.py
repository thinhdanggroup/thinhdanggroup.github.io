import re
import sys
import os
import shutil
from datetime import datetime
import glob


def clean_markdown(text):
    """
    Remove citation references and fix bibliography format in markdown text.

    This function:
    1. Removes patterns like .2, .4, etc. that appear after text (citation references)
    2. Converts bibliography format from "Title, [URL](URL)" to "[Title, ](URL)"
    3. Removes | characters from URLs

    Args:
        text (str): The input markdown text

    Returns:
        str: The text with citation references removed and bibliography format fixed
    """
    # Step 1: Remove citation references
    # Pattern to match citation references:
    # - A period followed by one or more digits
    # - Optionally followed by whitespace or end of string
    # - Not preceded by another digit (to avoid removing decimal numbers)

    # This pattern matches citations like .2, .4, etc. but avoids decimals like 3.14
    citation_pattern = r"(?<!\d)\.(\d+)(?=\s|$|[^\w])"

    # Replace the pattern with just a period (removing the number)
    cleaned_text = re.sub(citation_pattern, ".", text)

    # Clean up any double periods that might result
    cleaned_text = re.sub(r"\.\.+", ".", cleaned_text)

    # Step 2: Fix bibliography format
    # Pattern to match: "Number. Title, [URL](URL)" and convert to "Number. [Title, ](URL)"
    # The pattern captures: number, title/info text, URL in brackets, URL in parentheses
    bib_pattern = r"^(\d+\.\s*)(.+?),\s*\[([^\]]+)\]\(([^)]+)\)(.*)$"

    def fix_bibliography_line(match):
        number = match.group(1)  # "1. "
        title_info = match.group(2)  # "Title, accessed date"
        # match.group(3) is URL that was in brackets (unused)
        url = match.group(4)  # Actual URL
        trailing = match.group(5)  # Any trailing content

        # Remove | characters from URL
        title_info = (
            title_info.replace("|", "")
            .replace("\\", "")
            .replace("]", "")
            .replace("[", "")
        )

        clean_url = url.replace("|", "")

        # Return in format: "1. [Title, accessed date, ](clean_url)"
        return f"{number}[{title_info}, ]({clean_url}){trailing}"

    # Apply bibliography fixing line by line
    lines = cleaned_text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^\d+\.\s+.*\[.*\]\(.*\)", line):
            lines[i] = re.sub(bib_pattern, fix_bibliography_line, line)

    cleaned_text = "\n".join(lines)

    # Step 3: Remove | characters from any remaining URLs in markdown links
    cleaned_text = re.sub(r"\]\(([^)]*)\|([^)]*)\)", r"](\1\2)", cleaned_text)

    return cleaned_text


def process_file(input_file, output_file=None):
    """
    Process a markdown file to remove citation references.

    Args:
        input_file (str): Path to the input markdown file
        output_file (str): Path to the output file (optional)
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        cleaned_content = clean_markdown(content)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)
            print(f"Cleaned content written to: {output_file}")
        else:
            print(cleaned_content)

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)


def create_image_folder_and_move_banner(label, script_dir, blog_root):
    """
    Create image folder and move banner.png to assets/images/<label>/

    Args:
        label (str): The blog label (e.g., 'duck-db')
        script_dir (str): Path to the script directory
        blog_root (str): Path to the blog root directory
    """
    # Create target image directory
    image_dir = os.path.join(blog_root, "assets", "images", label)
    os.makedirs(image_dir, exist_ok=True)

    # Look for banner.png in script directory
    banner_source = os.path.join(script_dir, "banner.png")
    if os.path.exists(banner_source):
        banner_target = os.path.join(image_dir, "banner.png")
        shutil.move(banner_source, banner_target)
        print(f"Moved banner.png to: {banner_target}")
    else:
        print(f"Warning: banner.png not found in {script_dir}")


def create_blog_post(label, script_dir, blog_root):
    """
    Process markdown file and create blog post in _posts with proper naming

    Args:
        label (str): The blog label (e.g., 'duck-db')
        script_dir (str): Path to the script directory
        blog_root (str): Path to the blog root directory
    """
    # Look for input.md or output.md in script directory
    input_file = None
    for filename in ["input.md", "output.md"]:
        potential_file = os.path.join(script_dir, filename)
        if os.path.exists(potential_file):
            input_file = potential_file
            break

    if not input_file:
        print("Warning: No input.md or output.md found in script directory")
        return

    # Read and clean the markdown content
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned_content = clean_markdown(content)

    # Generate filename with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    post_filename = f"{current_date}-{label}.md"
    post_path = os.path.join(blog_root, "_posts", post_filename)

    # Write the cleaned content to the blog post
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(cleaned_content)

    print(f"Created blog post: {post_path}")


def move_html_files(label, script_dir, blog_root):
    """
    Move HTML files from script directory to assets/htmls with proper naming

    Args:
        label (str): The blog label (e.g., 'duck-db')
        script_dir (str): Path to the script directory
        blog_root (str): Path to the blog root directory
    """
    # Look for HTML files in script directory
    html_files = glob.glob(os.path.join(script_dir, "*.html"))

    if not html_files:
        print("No HTML files found in script directory")
        return

    htmls_dir = os.path.join(blog_root, "assets", "htmls")
    os.makedirs(htmls_dir, exist_ok=True)

    for html_file in html_files:
        # Get the original filename without path
        original_name = os.path.basename(html_file)

        # Create new filename with label
        name_without_ext = os.path.splitext(original_name)[0]
        new_filename = (
            f"{label}.html"
            if name_without_ext == "infographic"
            else f"{label}-{name_without_ext}.html"
        )

        target_path = os.path.join(htmls_dir, new_filename)
        shutil.move(html_file, target_path)
        print(f"Moved {original_name} to: {target_path}")


def prepare_blog(label):
    """
    Complete blog preparation workflow

    Args:
        label (str): The blog label (e.g., 'duck-db')
    """
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    blog_root = os.path.dirname(
        os.path.dirname(script_dir)
    )  # Go up two levels from script/fix_markdown

    print(f"Preparing blog with label: {label}")
    print(f"Script directory: {script_dir}")
    print(f"Blog root: {blog_root}")

    # Step 1: Create image folder and move banner.png
    create_image_folder_and_move_banner(label, script_dir, blog_root)

    # Step 2: Process markdown and create blog post
    create_blog_post(label, script_dir, blog_root)

    # Step 3: Move HTML files
    move_html_files(label, script_dir, blog_root)

    print(f"Blog preparation completed for label: {label}")


def main():
    """
    Main function to handle command line arguments and process files.
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python converter.py <label>                    # Prepare complete blog"
        )
        print(
            "  python converter.py <input_file> [output_file] # Legacy markdown cleaning"
        )
        print("Examples:")
        print("  python converter.py duck-db")
        print("  python converter.py input.md")
        print("  python converter.py input.md output.md")
        sys.exit(1)

    first_arg = sys.argv[1]

    # Check if first argument is a file (has extension) or a label
    if os.path.exists(first_arg) and first_arg.endswith(".md"):
        # Legacy mode: process markdown file
        input_file = first_arg
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        process_file(input_file, output_file)
    else:
        # New mode: prepare complete blog
        label = first_arg
        prepare_blog(label)


if __name__ == "__main__":
    main()
