import os
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from PIL import Image


class TitlePhotoTests(SimpleTestCase):
	def test_get_title_photo_downloads_and_validates_image(self):
		from imageapp.imageuploader import getTitlePhoto

		with tempfile.TemporaryDirectory() as media_root:
			def write_generated_image(prompt, output_path, **options):
				Image.new("RGB", (2, 2), color="blue").save(output_path, format="JPEG")
				return output_path

			with override_settings(MEDIA_ROOT=media_root, POLLINATIONS_API_KEY=""):
				with patch("pollinations.Pollinations.download_image", side_effect=write_generated_image) as download:
					image_path = getTitlePhoto(None, "Siargao Island Hopping")
					self.assertTrue(os.path.isfile(image_path))
					self.assertEqual(os.path.basename(image_path).split("_")[0], "siargao-island-hopping")
					download.assert_called_once()
					self.assertEqual(download.call_args.kwargs["prompt"], "Siargao Island Hopping")
					self.assertEqual(download.call_args.kwargs["model"], "flux")
