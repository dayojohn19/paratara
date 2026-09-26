from django.test import TestCase
from types import SimpleNamespace

from .views import _package_group_payload, _package_payload

# Create your tests here.

class ResortDetailsPayloadTests(TestCase):
	def setUp(self):
		self.place = SimpleNamespace(slug='siargao', placename='Siargao')
		self.resort = SimpleNamespace(
			id=12,
			slug='first-villa',
			name='first-villa',
			RealName='First Villa',
			websiteURL='',
			address='Tourism Road, General Luna',
			latitude=9.8,
			longitude=126.1,
			description='A quiet garden-side stay.',
		)

	def test_package_payload_includes_parent_resort_details(self):
		package = SimpleNamespace(
			id=34,
			title='Garden room',
			description='Room details',
			information='',
			price=1000,
			rating_average=0,
			rating_count=0,
			website='',
			ImageURL=SimpleNamespace(all=lambda: []),
		)

		payload = _package_payload(package, self.resort, self.place)

		self.assertEqual(payload['resortAddress'], self.resort.address)
		self.assertEqual(payload['resortLatitude'], self.resort.latitude)
		self.assertEqual(payload['resortLongitude'], self.resort.longitude)
		self.assertEqual(payload['resortDescription'], self.resort.description)

	def test_empty_package_group_includes_parent_resort_details(self):
		payload = _package_group_payload(
			SimpleNamespace(), self.resort, self.place, 'Activities', 'activity'
		)

		self.assertEqual(payload['resortAddress'], self.resort.address)
		self.assertEqual(payload['resortLatitude'], self.resort.latitude)
		self.assertEqual(payload['resortLongitude'], self.resort.longitude)
		self.assertEqual(payload['resortDescription'], self.resort.description)
