from django.test import TestCase
from .models import Site, Period, ClusiveUser

class SiteTestCase(TestCase):
    def setUp(self):
        cast_collegiate = Site.objects.create(name="CAST Collegiate", location="Wakefield, MA")

    def test_site_defaults(self):
        """ A newly created site has expected defaults """

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        self.assertEqual(cast_collegiate.language_code, 'EN')
        self.assertEqual(cast_collegiate.country_code, 'US')
        self.assertEqual(cast_collegiate.timezone, 'EST')

    def test_period_assignment_to_site(self):
        """ Multiple periods can created and assigned to the same site"""
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        udl_101 = Period.objects.create(name="Universal Design For Learning 101", site=cast_collegiate)
        udl_201 = Period.objects.create(name="Universal Design For Learning 201", site=cast_collegiate)

        self.assertEqual(cast_collegiate.period_set.count(), 2)

        self.assertEqual(udl_101.site.name, 'CAST Collegiate')
        self.assertEqual(udl_201.site.name, 'CAST Collegiate')

    def test_site_deletion_cascade_to_periods(self):
        """ If a site is deleted, all its associated periods are deleted """
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        Period.objects.create(name="Universal Design For Learning 101", site=cast_collegiate)
        Period.objects.create(name="Universal Design For Learning 201", site=cast_collegiate)

        self.assertEqual(Period.objects.count(), 2)

        cast_collegiate.delete()

        self.assertEqual(Period.objects.count(), 0)        