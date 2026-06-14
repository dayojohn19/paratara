from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
import json

from .date_patterns import expand_every_weekday_in_month
from .models import PackageReview, Packages


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


@override_settings(SECURE_SSL_REDIRECT=False)
class PackageReviewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='rater', password='testpass123')
        self.other_user = User.objects.create_user(username='second-rater', password='testpass123')
        self.package = Packages.objects.create(title='Island Hopping')

    def test_review_updates_package_rating_summary(self):
        review = PackageReview.objects.create(
            package=self.package,
            user=self.user,
            rating=5,
            comment='Excellent trip.'
        )
        self.package.refresh_from_db()
        self.assertEqual(self.package.rating_count, 1)
        self.assertEqual(self.package.rating_average, Decimal('5.00'))

        PackageReview.objects.create(
            package=self.package,
            user=self.other_user,
            rating=3,
            comment='Okay.'
        )
        self.package.refresh_from_db()
        self.assertEqual(self.package.rating_count, 2)
        self.assertEqual(self.package.rating_average, Decimal('4.00'))

        review.delete()
        self.package.refresh_from_db()
        self.assertEqual(self.package.rating_count, 1)
        self.assertEqual(self.package.rating_average, Decimal('3.00'))

    def test_submit_review_endpoint_creates_and_updates_current_users_review(self):
        self.client.force_login(self.user)
        url = reverse('resorts:submit_package_review', args=[self.package.id])

        response = self.client.post(
            url,
            data=json.dumps({'rating': 4, 'comment': 'Clean room'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['created'])
        self.assertEqual(data['rating_average'], 4.0)
        self.assertEqual(PackageReview.objects.count(), 1)

        response = self.client.post(
            url,
            data={'rating': 2, 'comment': 'Changed my mind'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['created'])
        self.assertEqual(data['rating_average'], 2.0)
        self.assertEqual(PackageReview.objects.count(), 1)
        self.assertEqual(PackageReview.objects.get().comment, 'Changed my mind')

    def test_submit_review_endpoint_rejects_rating_outside_one_to_five(self):
        self.client.force_login(self.user)
        url = reverse('resorts:submit_package_review', args=[self.package.id])

        response = self.client.post(url, data={'rating': 6, 'comment': 'Too high'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PackageReview.objects.count(), 0)

    def test_package_reviews_endpoint_loads_reviews_only_when_requested(self):
        PackageReview.objects.create(
            package=self.package,
            user=self.user,
            rating=5,
            comment='Excellent.'
        )
        PackageReview.objects.create(
            package=self.package,
            user=self.other_user,
            rating=4,
            comment='Good.'
        )

        url = reverse('resorts:package_reviews', args=[self.package.id])
        response = self.client.get(url, {'limit': 1})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['rating_count'], 2)
        self.assertEqual(len(data['reviews']), 1)
        self.assertTrue(data['has_more'])
        self.assertIsNotNone(data['next_offset'])
