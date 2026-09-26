import json
import os
import tempfile
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, override_settings

from singlepage2.htmlwriter import generate_blog_page
from singlepage2.views import _patch_blog_template_metadata

# Create your tests here.


class BlogMetadataTemplateEditTests(SimpleTestCase):
    def test_generator_uses_summary_as_h1_and_keeps_title(self):
        with tempfile.TemporaryDirectory() as base_dir:
            blog_object = Mock(cover_image_url="/static/images/default-cover.jpg")
            generated_image_path = os.path.join(
                base_dir, "media", "generated_title_images", "siargao-cover.png"
            )
            with override_settings(
                BASE_DIR=base_dir,
                MEDIA_ROOT=os.path.join(base_dir, "media"),
                MEDIA_URL="/media/",
            ):
                with patch("singlepage2.htmlwriter.optimize_file"), patch(
                    "imageapp.imageuploader.getTitlePhoto",
                    return_value=generated_image_path,
                ) as get_title_photo:
                    html = generate_blog_page(
                        None,
                        "Siargao",
                        "Island Hopping Guide",
                        "<p>Plan a day on the water.</p>",
                        faq_entries=[{
                            "name": "What should I bring?",
                            "acceptedAnswer": {"text": "Bring water and sun protection."},
                        }],
                        blog_searchable_keys_description="Island hopping tips for Siargao.",
                        category="Guide",
                        summary="A practical guide to Siargao island hopping.",
                        blog_obj=blog_object,
                    )

            self.assertIn(
                '<h1 id="blog-summary">A practical guide to Siargao island hopping.</h1>',
                html,
            )
            self.assertIn(
                '<p id="blog-title" class="blog-hero-title">Island Hopping Guide</p>',
                html,
            )
            get_title_photo.assert_called_once_with(None, "Island Hopping Guide")
            self.assertEqual(
                blog_object.cover_image_url,
                "/media/generated_title_images/siargao-cover.png",
            )
            blog_object.save.assert_called_once_with(update_fields=["cover_image_url"])

    def test_metadata_update_moves_page_and_redirects_old_slug(self):
        html = '''<!doctype html>
        <html><head>
            <title>Old title</title>
            <link rel="canonical" href="https://www.paratara.com/pages/blog/siargao/old-title/">
            <meta property="og:url" content="https://www.paratara.com/pages/blog/siargao/old-title/">
            <meta property="og:title" content="Old title">
            <meta name="twitter:title" content="Old title">
            <script type="application/ld+json">{"@type":"Article","headline":"Old title","url":"https://www.paratara.com/pages/blog/siargao/old-title/"}</script>
        </head><body>
            <header class="blog-hero"><span class="blog-kicker">Guide · Siargao</span><h1>Old title</h1></header>
            <div id="blog-editable-body"></div>
        </body></html>'''

        with tempfile.TemporaryDirectory() as base_dir:
            old_directory = os.path.join(base_dir, "singlepage2", "templates", "blogs", "siargao")
            os.makedirs(old_directory)
            old_path = os.path.join(old_directory, "old-title.html")
            with open(old_path, "w", encoding="utf-8") as template_file:
                template_file.write(html)

            with override_settings(BASE_DIR=base_dir):
                updated, new_path, error, new_url = _patch_blog_template_metadata(
                    "Updated <Guide>",
                    "Summary & practical details",
                    place_slug="siargao",
                    title_slug="old-title",
                    page_url="/pages/blog/siargao/old-title/",
                )

            self.assertTrue(updated, error)
            self.assertEqual(new_url, "/pages/blog/siargao/updated-guide/")
            self.assertTrue(os.path.exists(new_path))
            with open(new_path, "r", encoding="utf-8") as template_file:
                updated_html = template_file.read()
            self.assertIn('<h1 id="blog-summary">Summary &amp; practical details</h1>', updated_html)
            self.assertIn('<p class="blog-hero-title" id="blog-title">Updated &lt;Guide&gt;</p>', updated_html)
            self.assertIn('https://www.paratara.com/pages/blog/siargao/updated-guide/', updated_html)

            schema_script = BeautifulSoup(updated_html, "html.parser").find(
                "script", attrs={"type": "application/ld+json"}
            )
            schema = json.loads(schema_script.string or schema_script.get_text())
            self.assertEqual(schema["headline"], "Updated <Guide> — Siargao")
            self.assertEqual(schema["url"], "https://www.paratara.com/pages/blog/siargao/updated-guide/")

            with open(old_path, "r", encoding="utf-8") as template_file:
                redirect_html = template_file.read()
            self.assertIn('content="0;url=/pages/blog/siargao/updated-guide/"', redirect_html)

    def test_metadata_update_supports_legacy_header_markup(self):
        html = """<!doctype html>
        <html><head><title>Old title</title></head><body>
            <header><h1>Old title</h1></header>
            <main><div id="blog-editable-body"><p>Article text.</p></div></main>
        </body></html>"""

        with tempfile.TemporaryDirectory() as base_dir:
            blog_directory = os.path.join(base_dir, "singlepage2", "templates", "blogs", "siargao")
            os.makedirs(blog_directory)
            old_path = os.path.join(blog_directory, "old-title.html")
            with open(old_path, "w", encoding="utf-8") as template_file:
                template_file.write(html)

            with override_settings(BASE_DIR=base_dir):
                updated, new_path, error, _ = _patch_blog_template_metadata(
                    "Updated title",
                    "A saved summary",
                    place_slug="siargao",
                    title_slug="old-title",
                    page_url="/pages/blog/siargao/old-title/",
                )

            self.assertTrue(updated, error)
            with open(new_path, "r", encoding="utf-8") as template_file:
                updated_html = template_file.read()
            self.assertIn('class="blog-hero"', updated_html)
            self.assertIn('<h1 id="blog-summary">A saved summary</h1>', updated_html)
            self.assertIn('<p class="blog-hero-title" id="blog-title">Updated title</p>', updated_html)
