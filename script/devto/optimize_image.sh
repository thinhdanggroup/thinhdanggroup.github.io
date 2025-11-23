#!/bin/bash
# Script to optimize images for dev.to
# Dev.to recommends images under 1MB for best performance

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <image_path>"
    echo "Example: $0 /path/to/banner.png"
    exit 1
fi

IMAGE_PATH="$1"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: File not found: $IMAGE_PATH"
    exit 1
fi

# Check if ImageMagick or sips is available
if command -v convert &> /dev/null; then
    echo "Using ImageMagick to optimize..."
    BACKUP="${IMAGE_PATH}.backup"
    cp "$IMAGE_PATH" "$BACKUP"

    # Compress PNG with quality 85, resize if needed
    convert "$IMAGE_PATH" -quality 85 -resize '1200x630>' "$IMAGE_PATH"

    echo "Original size: $(du -h "$BACKUP" | cut -f1)"
    echo "Optimized size: $(du -h "$IMAGE_PATH" | cut -f1)"
    echo "Backup saved to: $BACKUP"

elif command -v sips &> /dev/null; then
    echo "Using sips (macOS) to optimize..."
    BACKUP="${IMAGE_PATH}.backup"
    cp "$IMAGE_PATH" "$BACKUP"

    # Resize and compress (sips is available on macOS)
    sips -Z 1200 "$IMAGE_PATH" --setProperty formatOptions 85

    echo "Original size: $(du -h "$BACKUP" | cut -f1)"
    echo "Optimized size: $(du -h "$IMAGE_PATH" | cut -f1)"
    echo "Backup saved to: $BACKUP"
else
    echo "Error: Neither ImageMagick (convert) nor sips is available"
    echo "Please install ImageMagick: brew install imagemagick"
    exit 1
fi

echo ""
echo "✓ Image optimized successfully!"
echo "If you're satisfied with the result, you can delete the backup:"
echo "  rm $BACKUP"
