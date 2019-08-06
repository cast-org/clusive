from django.test import TestCase
from .models import Site, Period, ClusiveUser
from django.core.exceptions import ValidationError

class SiteTestCase(TestCase):
    def setUp(self):
        cast_collegiate = Site.objects.create(name="CAST Collegiate", location="Wakefield, MA")
        idrc_institute = Site.objects.create(name="IDRC Institute", location="Toronto, ON", country_code="ca")

    def test_site_defaults(self):
        """ A newly created site has expected defaults """

        cast_collegiate = Site.objects.get(name="CAST Collegiate")        
        self.assertEqual(cast_collegiate.country_code, 'us')
        self.assertEqual(cast_collegiate.timezone, 'America/New_York')
        self.assertEqual(cast_collegiate.anon_id, None)

    def test_site_anon_id(self):
        """ A site can have an anon_id set manually """
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        cast_collegiate.anon_id = "Site1"        
        
        try:
            cast_collegiate.full_clean()
        except ValidationError as e:
            self.fail("Validation should not have failed")            

        self.assertEqual(cast_collegiate.anon_id, "Site1")        

    def test_site_anon_id_unique(self):
        """ Two sites cannot have the same anon_id"""

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        idrc_institute = Site.objects.get(name="IDRC Institute")
        cast_collegiate.anon_id = "Site1"
        cast_collegiate.save()

        idrc_institute.anon_id = "Site1"

        try:
            idrc_institute.full_clean()
            self.fail("Validation should have failed due to same anon_id")
        except ValidationError as e:                    
            self.assertEqual(e.message_dict["anon_id"][0], "Site with this Anon id already exists.")        

    def test_site_timezone_validation(self):
        """ A site won't accept an invalid timezone"""

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        cast_collegiate.timezone = "America/Boston"

        try:
            cast_collegiate.full_clean()            
        except ValidationError as e:                    
            self.assertEqual(e.message_dict["timezone"][0], "Value 'America/Boston' is not a valid choice.")
        
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