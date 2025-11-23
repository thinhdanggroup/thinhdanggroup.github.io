# Dev.to Blog Publisher

This script publishes your Jekyll blog posts to dev.to automatically.

## Features

- ✅ Converts Jekyll front matter to dev.to format
- ✅ Converts relative image URLs to absolute URLs
- ✅ Automatic image optimization script included
- ✅ Preserves canonical URLs (points back to your original blog)
- ✅ Supports publishing as draft or published
- ✅ Handles tags (up to 4 tags per dev.to limits)
- ✅ Dry-run mode for testing
- ✅ Batch publishing (single post, recent N posts, or all posts)

## Setup

### 1. Get Your Dev.to API Key

1. Go to https://dev.to/settings/extensions
2. Generate an API key
3. Copy the key (you'll need it in the next step)

### 2. Install Dependencies

```bash
make devto-install
```

Or manually:

```bash
pip install -r script/devto/requirements.txt
```

### 3. Configure

```bash
# Copy the config template
cp script/devto/config.json.template script/devto/config.json

# Edit the config file and add your API key
# Edit script/devto/config.json and replace YOUR_DEVTO_API_KEY_HERE with your actual API key
```

### 4. Configuration Options

Edit `script/devto/config.json`:

```json
{
  "api_key": "YOUR_DEVTO_API_KEY_HERE",  // Required: Your dev.to API key
  "base_url": "https://thinhdanggroup.github.io",  // Your blog's base URL
  "canonical_url_template": "https://thinhdanggroup.github.io/{slug}/",  // Template for canonical URLs
  "organization_id": null,  // Optional: If publishing under an organization
  "default_series": null   // Optional: Default series name for all posts
}
```

## Usage

### Quick Start with Makefile

```bash
# Test with dry-run (recommended first time)
make devto-dry-run

# Publish a specific post as draft
make devto-post POST=2023-07-20-prompt-engineering

# Publish 5 most recent posts as drafts
make devto-recent N=5

# Publish all posts as drafts
make devto-all
```

### Advanced Usage

#### Publish a specific post as a draft

```bash
python script/devto/publish_to_devto.py --post 2023-07-20-prompt-engineering --draft
```

#### Publish a specific post as published

```bash
python script/devto/publish_to_devto.py --post 2023-07-20-prompt-engineering
```

#### Publish 5 most recent posts as drafts

```bash
python script/devto/publish_to_devto.py --recent 5 --draft
```

#### Publish all posts as drafts

```bash
python script/devto/publish_to_devto.py --all --draft
```

#### Dry run (test without actually publishing)

```bash
python script/devto/publish_to_devto.py --all --dry-run
```

#### Disable image uploads (use absolute URLs instead)

```bash
python script/devto/publish_to_devto.py --post 2023-07-20-prompt-engineering --no-upload-images
```

## How It Works

1. **Reads Blog Posts**: The script reads markdown files from your `_posts` directory
2. **Extracts Front Matter**: Parses the Jekyll YAML front matter
3. **Converts Content**: 
   - Converts relative image paths to absolute URLs
   - Maps Jekyll front matter to dev.to format
   - Extracts tags (up to 4 tags per dev.to limits)
   - Adds cover/banner image from Jekyll front matter
   - Adds footer with link back to original blog post
4. **Sets Canonical URL**: Points back to your original blog post
5. **Publishes**: Uses dev.to API to create the article (dev.to automatically fetches and caches images)

## Front Matter Mapping

Your Jekyll front matter is mapped to dev.to as follows:

| Jekyll | Dev.to | Notes |
|--------|--------|-------|
| `title` | `title` | Required |
| `tags` | `tags` | Limited to 4 tags |
| `header.overlay_image` | `main_image` | Cover image (priority 1) |
| `header.teaser` | `main_image` | Cover image (priority 2) |
| `header.image` | `main_image` | Cover image (priority 3) |
| `image` | `main_image` | Cover image (priority 4) |
| `excerpt` | `description` | Article description |
| `series` | `series` | Series name |

## Image Handling

The script converts relative image paths to absolute URLs pointing to your blog:

```markdown
# Before (in your Jekyll blog)
![Image](/assets/images/banner.png)

# After (in dev.to)
![Image](https://thinhdanggroup.github.io/assets/images/banner.png)
```

Dev.to will automatically fetch and cache these images from your blog when you publish.

### Important: Image Optimization

**⚠️ Images must be optimized before publishing!** 

Dev.to's CDN may fail to process large images (>1-2MB). Always optimize your images first:

```bash
# Optimize banner image
./script/devto/optimize_image.sh assets/images/your-post/banner.png

# Or using make
make devto-optimize-image IMAGE=assets/images/your-post/banner.png
```

**Recommended**: Keep images under 700KB for best results.

### Cover Images/Banners

The script automatically extracts cover images from your Jekyll front matter. It checks in this priority order:

1. `header.overlay_image` - Main overlay banner
2. `header.teaser` - Teaser image
3. `header.image` - Header image
4. `image` - Direct image field

Banner images are uploaded to dev.to's CDN, ensuring they display correctly.

## Canonical URLs

All published articles include:
1. **Canonical URL metadata** - Points back to your original blog post, telling search engines that your blog is the original source
2. **Footer reference** - Adds a visible link at the end of each article:
   ```
   ---
   
   *This article was originally published on [ThinhDangGroup Blog](https://thinhdanggroup.github.io/your-post/)*
   ```

This protects your SEO and drives traffic back to your main blog.

## Tips

1. **Start with Dry Run**: Always test with `--dry-run` first
2. **Use Drafts**: Publish as drafts first (`--draft`) to review before publishing
3. **Optimize Images First**: Run `./script/devto/optimize_image.sh` on banner images before publishing
4. **Check Tags**: Dev.to only allows 4 tags per article, the script will use the first 4
5. **Image Quality**: Make sure all images are publicly accessible and under 700KB
6. **Canonical URLs**: This ensures your original blog maintains SEO value

## Troubleshooting

### "Authentication failed" Error

- Check that your API key is correct in `config.json`
- Make sure the API key is still valid on dev.to

### "Validation error"

- Check that the post has a title
- Verify that tags are valid (no spaces, lowercase)
- Ensure images are accessible

### Images Not Displaying

- Verify that image paths in your markdown start with `/assets/`
- Check that images are publicly accessible
- Make sure `base_url` in config is correct
- **Image size**: Dev.to recommends images under 1MB. If your banner is too large (>2MB), dev.to's CDN may fail to process it

#### Optimizing Large Images

If your banner images are too large, optimize them first:

```bash
# Using the provided script
./script/devto/optimize_image.sh assets/images/your-banner/banner.png

# Or using ImageMagick directly
brew install imagemagick  # if not installed
convert your-banner.png -quality 85 -resize '1200x630>' optimized-banner.png

# Or using macOS sips
sips -Z 1200 your-banner.png --setProperty formatOptions 85
```

**Recommended banner size**: 1200x630px, under 500KB for best performance

## API Rate Limits

Dev.to has rate limits on their API:
- 30 requests per 30 seconds (per API key)
- The script publishes posts one at a time to respect these limits

## Support

If you encounter issues:
1. Run with `--dry-run` to see what would be published
2. Check the logs for error messages
3. Verify your config.json is correct
4. Make sure your API key has the correct permissions

## References

- [Dev.to API Documentation](https://developers.forem.com/api)
- [Dev.to Article API](https://developers.forem.com/api/v0#tag/articles)
