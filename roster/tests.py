from django.test import TestCase
from .models import Site, Period, ClusiveUser
from django.core.exceptions import ValidationError

def set_up_test_sites():
        Site.objects.create(name="CAST Collegiate", city="Wakefield", state_or_province="MA", country="USA")
        Site.objects.create(name="IDRC Institute", city="Toronto", state_or_province="ON", country="Canada")
        Site.objects.create(name="Underdetailed University")

def set_up_test_periods():
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        Period.objects.create(name="Universal Design For Learning 101", site=cast_collegiate)
        Period.objects.create(name="Universal Design For Learning 201", site=cast_collegiate)

class SiteTestCase(TestCase):
    def setUp(self):
        set_up_test_sites()

    def test_defaults(self):
        """ A created site has expected defaults if not set """
        underdetailed_university = Site.objects.get(name="Underdetailed University")
                  
        self.assertEqual(underdetailed_university.timezone, 'America/New_York')
        self.assertEqual(underdetailed_university.anon_id, None)
        self.assertEqual(underdetailed_university.city, "")
        self.assertEqual(underdetailed_university.state_or_province, "")
        self.assertEqual(underdetailed_university.country, "")

    def test_manual_anon_id(self):
        """ A site can have an anon_id set manually """
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        cast_collegiate.anon_id = "Site1"        
        
        try:
            cast_collegiate.full_clean()
        except ValidationError as e:
            self.fail("Validation should not have failed")            

        self.assertEqual(cast_collegiate.anon_id, "Site1")        

    def test_anon_id_unique_enforcement(self):
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

    def test_timezone_validation(self):
        """ A site won't accept an invalid timezone"""

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        cast_collegiate.timezone = "America/Boston"

        try:
            cast_collegiate.full_clean()            
        except ValidationError as e:                    
            self.assertEqual(e.message_dict["timezone"][0], "Value 'America/Boston' is not a valid choice.")
        
    def test_site_deletion_cascade_to_periods(self):
        """ If a site is deleted, all its associated periods are deleted """
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        Period.objects.create(name="Universal Design For Learning 101", site=cast_collegiate)
        Period.objects.create(name="Universal Design For Learning 201", site=cast_collegiate)

        self.assertEqual(Period.objects.count(), 2)

        cast_collegiate.delete()

        self.assertEqual(Period.objects.count(), 0)                

class PeriodTestCase(TestCase):        

    def setUp(self):        
        set_up_test_sites()
        set_up_test_periods()

    def test_site_assignment(self):
        """ Multiple periods can created and assigned to the same site"""        

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        udl_101 = Period.objects.get(name="Universal Design For Learning 101")
        udl_201 = Period.objects.get(name="Universal Design For Learning 201")

        self.assertEqual(cast_collegiate.period_set.count(), 2)

        self.assertEqual(udl_101.site.name, 'CAST Collegiate')
        self.assertEqual(udl_201.site.name, 'CAST Collegiate')        

    def test_manual_anon_id(self):
        """ A period can have an anon_id set manually """
        udl_101 = Period.objects.get(name="Universal Design For Learning 101")
        udl_101.anon_id = "Period1"        
        
        try:
            udl_101.full_clean()
        except ValidationError as e:
            self.fail("Validation should not have failed")            

        self.assertEqual(udl_101.anon_id, "Period1")        

    def test_anon_id_unique_enforcement(self):
        """ Two periods cannot have the same anon_id"""

        udl_101 = Period.objects.get(name="Universal Design For Learning 101")
        udl_201 = Period.objects.get(name="Universal Design For Learning 201")
        udl_101.anon_id = "Period1"
        udl_101.save()

        udl_201.anon_id = "Period1"

        try:
            udl_201.full_clean()
            self.fail("Validation should have failed due to same anon_id")
        except ValidationError as e:                    
            self.assertEqual(e.message_dict["anon_id"][0], "Period with this Anon id already exists.")                