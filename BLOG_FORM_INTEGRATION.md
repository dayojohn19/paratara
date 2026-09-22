# Quick Integration Guide

## Connect the Blog Form to Your Django Project

### Step 1: Ensure singlepage2 URLs are Included

Open your **main project `urls.py`** (the one in your project root, not singlepage2):

```python
# project/urls.py or whatever your main urls file is called
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # ... other paths ...
    
    # Add this line if not already present:
    path('', include('singlepage2.urls')),  # This includes singlepage2 app URLs
]
```

### Step 2: Make Sure singlepage2 is in INSTALLED_APPS

Open your **settings.py**:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other apps ...
    'singlepage2',  # Make sure this exists
    'home',
    'apis',
    # ... other apps ...
]
```

### Step 3: Ensure Login is Required

The blog form requires login (`@login_required` decorator).

Make sure you have login URLs configured:

```python
# settings.py
LOGIN_URL = 'login'  # or whatever your login URL name is
LOGIN_REDIRECT_URL = '/'
```

### Step 4: Database Migrations

No new models were created, so no migrations needed. The form uses existing `Blogs` and `Places_v2` models.

---

## Test the Form

### Option A: Local Development
```bash
# In your terminal, in your project directory:
python manage.py runserver

# Then visit:
# http://localhost:8000/blog/create/
```

### Option B: Check if working
```bash
# Check if URL patterns are correct:
python manage.py show_urls | grep blog

# Should show something like:
# /blog/create/                    blog_form_view
# /blog/submit/                    create_blog_view
# /api/places/                     get_places_json
```

---

## Common Integration Issues

### Issue: "Page not found" (404)
**Solution:** 
- Check that `singlepage2` is in `INSTALLED_APPS`
- Check that URL patterns are included in main `urls.py`
- Try `python manage.py check`

### Issue: "Login required" redirect
**Solution:**
- Make sure you're logged in before accessing `/blog/create/`
- Or remove `@login_required` from `blog_form_view()` in `htmlwriter_noai.py` if you want public access

### Issue: "No module named 'singlepage2'"
**Solution:**
- Make sure the path is correct in your `urls.py`
- The import should be: `from . import views` or `path('', include('singlepage2.urls'))`

### Issue: Form appears but places autocomplete is empty
**Solution:**
- Check that `Places_v2` model has data
- Verify your database connection is working
- Check Django logs for SQL errors

---

## File Locations Reference

```
your-project/
├── manage.py
├── your_project/
│   ├── settings.py          ← Update INSTALLED_APPS here
│   ├── urls.py              ← Include singlepage2.urls here
│   └── wsgi.py
├── singlepage2/
│   ├── urls.py              ← ALREADY UPDATED ✓
│   ├── htmlwriter_noai.py   ← NEW FILE ✓
│   ├── views.py
│   ├── models.py
│   └── templates/
│       └── singlepage2/
│           └── blog_form.html   ← NEW FILE ✓
├── apis/
│   └── models.py            ← Uses Blogs model from here
├── home/
│   └── models.py            ← Uses Places_v2 model from here
└── BLOG_FORM_SETUP.md       ← NEW FILE ✓
```

---

## What Happens When Form is Submitted

1. User fills form and clicks "Create Blog Post"
2. Form data is sent to `/blog/submit/` (POST request)
3. `create_blog_view()` processes:
   - Validates required fields (place name, title)
   - Parses FAQ JSON data
   - Calls `generate_blog_object()` to save to database
   - Calls `generate_blog_page()` to create HTML file
   - Shows success message
   - Redirects back to form
4. Blog post is now:
   - Saved in database (Blogs model)
   - Available as HTML file at `singlepage2/templates/blogs/[place-slug]/[title-slug].html`
   - Accessible via existing blog URL patterns

---

## Example Django URL Config

If your main `urls.py` looks different, here's a complete example:

```python
# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Blog and single page routes
    path('', include('singlepage2.urls')),
    
    # API routes
    path('apis/', include('apis.urls')),
    
    # Home routes
    path('home/', include('home.urls')),
    
    # Auth routes (if you have them)
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## Next: Access the Form

Once everything is set up:

**Local:** http://localhost:8000/blog/create/
**Production:** https://yourdomain.com/blog/create/

---

Need help? Check `BLOG_FORM_SETUP.md` for detailed documentation.
