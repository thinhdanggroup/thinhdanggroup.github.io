#!/bin/bash

# Image optimization script for Jekyll blog
# Requires: imagemagick, optipng, jpegoptim

echo "Starting image optimization..."

# Create optimized directory if it doesn't exist
mkdir -p assets/images/optimized

# Function to optimize JPEG images
optimize_jpeg() {
    local file="$1"
    echo "Optimizing JPEG: $file"

    # Resize large images to max 1200px width while maintaining aspect ratio
    magick "$file" -resize "1200x1200>" -quality 80 -strip "$file.tmp"

    # Further optimize with jpegoptim
    jpegoptim --max=80 --strip-all "$file.tmp"

    # Replace original
    mv "$file.tmp" "$file"
}

# Function to optimize PNG images
optimize_png() {
    local file="$1"
    echo "Optimizing PNG: $file"

    # Resize large images
    magick "$file" -resize "1200x1200>" -strip "$file.tmp"

    # Optimize with optipng
    optipng -o7 "$file.tmp"

    # Replace original
    mv "$file.tmp" "$file"
}

# Find and optimize images
find assets/images -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -size +100k | while read file; do
    optimize_jpeg "$file"
done

find assets/images -type f -iname "*.png" -size +100k | while read file; do
    optimize_png "$file"
done

echo "Image optimization complete!"

# Show size comparison
echo "Checking largest remaining images..."
find assets/images -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -exec ls -lh {} + | sort -k 5 -hr | head -10