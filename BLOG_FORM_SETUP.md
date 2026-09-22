# Blog Form - Non-AI Version Setup Guide

## Overview
This is a form-based blog creation system that **does NOT rely on AI**. Users fill out a form to create blog posts, which are automatically saved to the database and generated as optimized HTML pages.

## Files Created

### 1. **blog_form.html** 
   - Location: `singlepage2/templates/singlepage2/blog_form.html`
   - A comprehensive HTML form with:
     - Basic information (place name, title, category)
     - Blog content (main text, summary, meta description)
     - Media & SEO fields (cover image, keywords, coordinates)
     - FAQ section with dynamic add/remove functionality
     - Character counters and help text
     - Responsive design for mobile and desktop

### 2. **htmlwriter_noai.py**
   - Location: `singlepage2/htmlwriter_noai.py`
   - Core functions:
     - `generate_blog_object()` - Creates blog in database
     - `generate_blog_page()` - Generates SEO-optimized HTML
     - `render_faq_section()` - Creates FAQ HTML with schema
     - `blog_form_view()` - Displays the form
     - `create_blog_view()` - Processes form submission
     - `get_places_json()` - API endpoint for autocomplete

### 3. **urls.py** (Updated)
   - Location: `singlepage2/urls.py`
   - New URL routes:
     - `/blog/create/` - Display form
     - `/blog/submit/` - Process form submission
     - `/api/places/` - Get places for autocomplete

---

## How to Use

### Step 1: Navigate to the Form
Go to: `http://yourdomain/blog/create/`

### Step 2: Fill Out the Form

#### **Basic Information Section**
- **Place Name** ⭐ Required - Select or type an existing place
- **Blog Title** ⭐ Required - Main title of your blog post
- **Category** - Choose from: Guide, Story, Tip and Trick, Explore, Product
- **Read Time** - Auto-calculated but can be overridden (minutes)

#### **Blog Content Section**
- **Summary** - Short description (max 400 chars)
- **Main Blog Content** - Full blog post content (supports HTML)
- **Meta Description** - For search engines (max 160 chars)

#### **Media & SEO Section**
- **Cover Image URL** - Full URL to blog header image
- **Searchable Keywords** - Comma-separated keywords
- **SEO Title** - Alternative title for search engines
- **Longitude/Latitude** - Geographic coordinates (optional)

#### **FAQ Section**
- Click "**+ Add FAQ Item**" to add questions
- The category you select will suggest relevant FAQ questions automatically
- Fill in both the question and answer
- Click "**Remove This Question**" to delete a FAQ item

### Step 3: Submit
Click "**📤 Create Blog Post**" to save

---

## Data Flow

```
Form Submission
    ↓
generate_blog_object()
    ├── Find/validate place
    ├── Clean and normalize data
    ├── Calculate read time
    ├── Check for duplicates
    └── Save to Blogs model
    ↓
generate_blog_page()
    ├── Create folder structure
    ├── Generate FAQ schema (JSON-LD)
    ├── Generate Article schema (JSON-LD)
    ├── Build SEO-optimized HTML
    └── Save .html file to disk
    ↓
Success Message & Redirect to Form
```

---

## Database Fields Used

From `apis.models.Blogs`:
- `category` - Blog category (choices)
- `blogplace` - Foreign key to Places_v2
- `title` - Blog title
- `seo_title` - SEO-specific title
- `textContent` - Main blog content
- `summarize` - Short summary
- `meta_description` - SEO meta tag
- `readtime` - Estimated read time (int)
- `cover_image_url` - Cover image URL
- `faq_entries` - FAQ data (JSON)
- `searchable_keywords` - Keywords for search
- `longitude` - Latitude coordinate
- `latitude` - Longitude coordinate
- `timestamp` - Auto-created timestamp
- `created_at` - Auto-created datetime

---

## Key Features

✅ **No AI Required** - Everything is form-based  
✅ **Auto-Generate HTML** - SEO-optimized pages created instantly  
✅ **FAQ Management** - Dynamic add/remove FAQ items  
✅ **Schema Markup** - Auto-generated JSON-LD for SEO  
✅ **Duplicate Prevention** - Checks for existing blogs  
✅ **Character Counters** - Real-time character tracking  
✅ **Category Suggestions** - Auto-suggest FAQ based on category  
✅ **Responsive Form** - Works on all devices  
✅ **Place Autocomplete** - Search existing places  
✅ **Error Handling** - User-friendly error messages  

---

## Customization

### Change Form Fields
Edit `blog_form.html` in the `<form>` section to add/remove fields

### Modify FAQ Questions
Edit the `FAQ_QUESTIONS_BY_CATEGORY` dictionary in `htmlwriter_noai.py`

### Change HTML Template
Edit the HTML generation in `generate_blog_page()` function in `htmlwriter_noai.py`

### Add Validation
Add custom validation in `create_blog_view()` before saving

### Styling
Modify the `<style>` section in `blog_form.html` to change colors/fonts

---

## Example Blog Post Creation

```
Place Name: Siargao Island
Title: Best Time to Visit Siargao Island in 2026
Category: Guide
Summary: Discover the perfect season to visit Siargao with weather insights and travel tips
Content: <h2>Best Season</h2><p>October to May is ideal...</p>
Cover Image: https://example.com/siargao.jpg
Keywords: siargao, travel, island, philippines, tourism
Meta Description: Find the best time to visit Siargao Island with weather, crowds, and cost considerations.

FAQ:
Q: What is the best time to visit?
A: October to May offers the best weather...

Q: How much is the entrance fee?
A: Entry is generally free, but beach resorts charge day-use fees of 50-200 PHP...
```

---

## Troubleshooting

### "Place not found"
- Make sure the place exists in your `Places_v2` model
- Check spelling and capitalization

### "Blog with this title already exists"
- Each place can only have one blog with the same title
- Use a slightly different title or edit the existing one

### HTML not generating
- Check that `singlepage2/templates/blogs/` folder exists
- Ensure write permissions for the folder
- Check Django error logs

### FAQ not showing
- Ensure both question and answer fields are filled
- JSON format should be valid `[{"question": "...", "answer": "..."}, ...]`

### Form not appearing
- Make sure you're logged in (login_required decorator)
- Check that URLs are registered correctly in `urls.py`
- Clear browser cache

---

## Testing

### Quick Test
1. Create a test place in Places_v2 model
2. Go to `/blog/create/`
3. Fill out form with test data
4. Submit
5. Check database: `Blogs.objects.latest('created_at')`
6. Check file created: `singlepage2/templates/blogs/[place-slug]/[title-slug].html`

---

## Notes

- FAQ schema is automatically generated and embedded in the HTML
- Article schema is generated with automatic dates
- Canonical URLs are set to `https://www.paratara.com/pages/blog/...`
- Cover images must be full URLs (not local files)
- HTML content supports any valid HTML tags
- Read time is auto-calculated (185 words = 1 minute)

---

## Support

For issues or modifications, check:
1. Django error logs
2. Browser console (F12 → Console tab)
3. Database structure in `apis/models.py`
4. Form validation in `create_blog_view()`

---

**Created:** 2026-09-14
**Version:** 1.0 (Non-AI)
**Python Version:** 3.8+
**Django Version:** 3.2+
