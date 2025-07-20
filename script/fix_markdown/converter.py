import re
import sys
import os


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
        url_text = match.group(3)  # URL that was in brackets (unused)
        url = match.group(4)  # Actual URL
        trailing = match.group(5)  # Any trailing content

        # Remove | characters from URL
        title_info = title_info.replace("|", "").replace("\\", "").replace("]", "").replace("[", "")

        clean_url = url.replace("|", "")

        # Return in format: "1. [Title, accessed date, ](clean_url)"
        return f"{number}[{title_info}, ]({clean_url}){trailing}"

    # Apply bibliography fixing line by line
    lines = cleaned_text.split('\n')
    for i, line in enumerate(lines):
        if re.match(r"^\d+\.\s+.*\[.*\]\(.*\)", line):
            lines[i] = re.sub(bib_pattern, fix_bibliography_line, line)

    cleaned_text = '\n'.join(lines)

    # Step 3: Remove | characters from any remaining URLs in markdown links
    cleaned_text = re.sub(r'\]\(([^)]*)\|([^)]*)\)', r'](\1\2)', cleaned_text)

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


def main():
    """
    Main function to handle command line arguments and process files.
    """
    if len(sys.argv) < 2:
        print("Usage: python converter.py <input_file> [output_file]")
        print("Examples:")
        print("  python converter.py input.md")
        print("  python converter.py input.md output.md")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    process_file(input_file, output_file)


if __name__ == "__main__":
    main()
