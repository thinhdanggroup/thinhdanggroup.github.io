# Blog Performance Optimization Guide

This guide outlines the performance optimizations implemented for the ThinhDA blog and how to maintain them.

## 🚀 Implemented Optimizations

### 1. Image Optimization
- **Automatic compression** via GitHub Actions on every push
- **Manual optimization script** at `scripts/optimize-images.sh`
- **Responsive image component** at `_includes/responsive-image.html`
- **Lazy loading** enabled by default

**⚠️ Install Required Tools** (for manual optimization):
```bash
# macOS
brew install imagemagick jpegoptim optipng

# Ubuntu/Debian
sudo apt-get install imagemagick jpegoptim optipng

# Alternative: Use online tools or GitHub Actions for optimization
```

**Current large images that need optimization:**
- `assets/images/mcp-production-ready/banner.png` (1.5MB)
- `assets/images/graphql_fastapi/banner.jpg` (1.4MB)
- `assets/images/education/create_topic.png` (813KB)
- `assets/images/avatar.jpg` (745KB)

### 2. Caching Strategy
- **Service Worker** implemented for aggressive caching of assets
- **Browser caching** hints via preconnect and dns-prefetch
- **Jekyll incremental builds** enabled

### 3. Asset Optimization
- **CSS compression** enabled in Jekyll config
- **HTML compression** with aggressive settings
- **JavaScript minification** via UglifyJS

### 4. Loading Performance
- **Critical CSS preloading**
- **DNS prefetching** for external services
- **Lazy loading** for images
- **Service worker** for offline support

## 📊 Performance Metrics to Monitor

### Core Web Vitals
- **Largest Contentful Paint (LCP)**: Target < 2.5s
- **First Input Delay (FID)**: Target < 100ms
- **Cumulative Layout Shift (CLS)**: Target < 0.1

### Additional Metrics
- **First Contentful Paint (FCP)**: Target < 1.8s
- **Time to Interactive (TTI)**: Target < 3.8s
- **Total Blocking Time (TBT)**: Target < 200ms

## 🛠️ Maintenance Tasks

### Weekly
1. **Run image optimization script** (after installing tools):
   ```bash
   ./scripts/optimize-images.sh
   ```

2. **Check for large new images**:
   ```bash
   find assets/images -type f \( -name "*.jpg" -o -name "*.png" \) -size +500k -exec ls -lh {} +
   ```

### Monthly
1. **Update dependencies**:
   ```bash
   bundle update
   npm update
   ```

2. **Performance audit** using Lighthouse or PageSpeed Insights

3. **Review and update service worker cache** if needed

### Before Adding New Content
1. **Optimize images** before committing:
   - Resize to appropriate dimensions (max 1200px width for content images)
   - Compress JPEG to 80% quality
   - Use WebP format when possible

2. **Use responsive image component**:
   ```liquid
   {% include responsive-image.html 
      path="assets/images/your-image.jpg" 
      alt="Descriptive alt text" 
      caption="Optional caption" %}
   ```

## 🔧 Development Commands

### Build and Serve Locally
```bash
# Install dependencies
bundle install

# Build the site
bundle exec jekyll build

# Serve locally (with auto-reload)
bundle exec jekyll serve

# Access at http://localhost:4000
```

### Testing Performance
```bash
# Check site builds successfully
bundle exec jekyll build

# Find large images
find assets/images -type f \( -name "*.jpg" -o -name "*.png" \) -size +300k -exec ls -lh {} +
```

## 🔍 Performance Testing Tools

### Online Tools
- [Google PageSpeed Insights](https://pagespeed.web.dev/)
- [GTmetrix](https://gtmetrix.com/)
- [WebPageTest](https://www.webpagetest.org/)

### Browser DevTools
- Chrome Lighthouse
- Network tab for waterfall analysis
- Performance tab for runtime analysis

## 🎯 Performance Goals

| Metric | Target | Status |
|--------|--------|--------|
| Desktop PageSpeed Score | > 90 | ⏳ Test needed |
| Mobile PageSpeed Score | > 85 | ⏳ Test needed |
| LCP | < 2.5s | ⏳ Test needed |
| FID | < 100ms | ⏳ Test needed |
| CLS | < 0.1 | ⏳ Test needed |
| Jekyll Build | No errors | ✅ **Fixed** |

## 🚨 Common Performance Issues

### Large Images
- **Problem**: Images over 500KB significantly impact LCP
- **Solution**: Use the optimization script or resize manually

### Too Many Analytics Scripts
- **Problem**: Multiple tracking scripts block rendering (Heap, PostHog, Google Analytics)
- **Solution**: Consider consolidating or loading fewer analytics tools

### Unoptimized CSS/JS
- **Problem**: Large, unminified assets
- **Solution**: Ensure Jekyll compression is enabled ✅

### Missing Cache Headers
- **Problem**: Assets not cached by browsers
- **Solution**: Service worker is implemented ✅

## 📱 Mobile Optimization

- Images are responsive by default ✅
- Touch targets are appropriately sized ✅
- Text is readable without zooming ✅
- Service worker provides offline functionality ✅

## 🔄 Future Improvements

1. **Implement WebP format** with fallbacks
2. **Add critical CSS inlining**
3. **Implement resource hints** for better prefetching
4. **Consider a CDN** for global asset delivery
5. **Implement font optimization**
6. **Add performance monitoring** with real user metrics
7. **Reduce analytics overhead** (consider removing some tracking tools)

## 📝 Notes

- ✅ **Jekyll build issues resolved** - site now compiles without errors
- GitHub Pages has limitations on plugins, so some optimizations must be done at build time
- Service worker updates automatically but may need manual cache busting for major changes
- Image optimization is automated via GitHub Actions but should be checked regularly for new large assets
- **Immediate priority**: Optimize the 4 largest images (>745KB each)

---

**Last Updated**: January 2025  
**Performance Baseline**: Ready for testing after large image optimization 