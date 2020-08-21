from zipfile import ZipFile

from django.contrib.auth.models import User
from django.test import TestCase
# Create your tests here.
from django.urls import reverse

from roster.models import ClusiveUser, Period, Site
from .models import Book, Paradata, BookVersion, BookAssignment
from .parsing import TextExtractor


class LibraryTestCase(TestCase):

    def test_text_extraction(self):
        te = TextExtractor()
        result = te.extract(
            '<html><head><title>Hi</title></head><body><p>Some nice text.</p><script type="text/javascript">Script</script><p>More and nicer texts.</p></body></html>')
        self.assertEqual(result, "Some nice text. More and nicer texts. ")
        self.assertSetEqual({'and', 'some', 'more', 'nice', 'text'}, te.get_word_set(),
                            "Did not extract correct set of words")

    def test_parse_file(self):
        te = TextExtractor()
        zip = ZipFile('../content/serp-penguins/serp-penguins-1.epub')
        file = zip.open('OEBPS/content.xhtml')
        te.feed(file.read().decode('utf-8'))
        te.close()
        result = te.text
        self.assertRegex(result, "Penguins are funny birds")
        self.assertNotRegex(result, "Photo")
        word_set = te.get_word_set()
        print(word_set)
        self.assertTrue('penguin' in word_set, "Parser didn't find a penguin in the penguins article")
        self.assertFalse('1' in word_set, "Parser didn't exclude number")


class LibraryApiTestCase(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        cuser = ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST')
        cuser.save()
        self.book = Book.objects.create(title='Book One', description='')
        self.book.save()
        bv = BookVersion.objects.create(book=self.book, sortOrder=0)
        bv.save()
        para = Paradata.objects.create(book=self.book, user=cuser, lastVersion = bv)
        para.save()

    def test_setlocation_error_for_get(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get(reverse('setlocation'))
        self.assertEqual(response.status_code, 405)

    def test_setlocation_error_for_nonexistent_book(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.post(reverse('setlocation'), { 'book' : 999, 'version': '0', 'locator' : 'testtest'})
        self.assertEqual(response.status_code, 500)

    def test_setlocation(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.post(reverse('setlocation'), { 'book' : self.book.pk, 'version': '0', 'locator' : 'testtest'})
        self.assertEqual(response.status_code, 200)
        pd = Paradata.objects.get(book=self.book)
        self.assertEqual('testtest', pd.lastLocation)


class ShareFormTestCase(TestCase):

    def setUp(self) -> None:
        self.site = Site.objects.create(name='test site', anon_id='test site')
        self.period = Period.objects.create(site=self.site, name='test period', anon_id='test period')
        teacher = User.objects.create_user(username="user1", password="password1")
        self.cuser = ClusiveUser.objects.create(anon_id="T1", user=teacher, role='TE')
        self.cuser.periods.add(self.period)
        self.cuser.save()
        self.book = Book.objects.create(title='Book One', description='')
        login = self.client.login(username='user1', password='password1')

    def test_render(self):
        response = self.client.get(reverse('share', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Book One')
        self.assertContains(response, 'test period')

    def test_adds_assignments(self):
        # Add an assignment
        response = self.client.post(reverse('share', kwargs={'pk': self.book.pk}), { 'periods': self.period.pk})
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        assignments = BookAssignment.objects.all()
        self.assertEqual(1, len(assignments))

        # And remove it again
        response = self.client.post(reverse('share', kwargs={'pk': self.book.pk}), { })
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        assignments = BookAssignment.objects.all()
        self.assertEqual(0, len(assignments))

    def test_refuses_change_for_student(self):
        self.cuser.role = 'ST'
        self.cuser.save()
        response = self.client.post(reverse('share', kwargs={'pk': self.book.pk}), { 'periods': self.period.pk})
        self.assertEqual(403, response.status_code)
        self.assertEqual(0, len(BookAssignment.objects.all()))

    def test_does_not_change_periods_user_is_not_in(self):
        # Send two periods, but only the one the teacher is in should get changed.
        other_period = Period.objects.create(site=self.site, name='unassociated period', anon_id='u period')
        response = self.client.post(reverse('share', kwargs={'pk': self.book.pk}),
                                    { 'periods': [self.period.pk, other_period.pk]})
        print(response)
        self.assertFormError(response, 'form', 'periods', 'Select a valid choice. 2 is not one of the available choices.')

