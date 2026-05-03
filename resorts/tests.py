from django.test import TestCase

from .date_patterns import expand_every_weekday_in_month


class DatePatternExpansionTests(TestCase):
	def test_every_friday_in_january_2026(self):
		info = expand_every_weekday_in_month("Every Friday in January 2026")
		self.assertIsNotNone(info)
		days = [d["dateN"] for d in info["specific_dates"]]
		self.assertEqual(days, [2, 9, 16, 23, 30])

	def test_lowercase_of_variant(self):
		info = expand_every_weekday_in_month("every friday of jan 2026")
		self.assertIsNotNone(info)
		days = [d["dateN"] for d in info["specific_dates"]]
		self.assertEqual(days, [2, 9, 16, 23, 30])
