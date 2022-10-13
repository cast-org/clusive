import logging
import math
from zipfile import ZipFile

import dawn
from django.contrib.auth.models import User
from django.test import TestCase
# Create your tests here.
from django.urls import reverse

from roster.models import ClusiveUser, Period, Site
from .models import Book, Paradata, BookVersion, BookAssignment, Customization, \
    CustomVocabularyWord, ReadingLevel
from .parsing import TextExtractor

logger = logging.getLogger(__name__)

class LibraryTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(username="user1", password="password1")
        user.save()
        clusive_user = ClusiveUser.objects.create(anon_id="Student1", user=user, role='ST')
        clusive_user.save()
        book = Book.objects.create(id=1, owner=clusive_user, title='Foo', sort_title='Foo', author='Bar', sort_author='Bar')
        book.save()
        bv = BookVersion.objects.create(id=321, book=book, sortOrder=0)
        bv.save()

    def test_upload_create_page(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/library/upload/create')
        self.assertEqual(response.status_code, 200)

    def test_upload_replace_page(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/library/upload/replace/1/321')
        self.assertEqual(response.status_code, 200)

    def test_metadata_create_page(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/library/metadata/upload/1/321')
        self.assertEqual(response.status_code, 200)

    def test_metadata_edit_page(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/library/metadata/edit/1')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/library/metadata/edit/1/321')
        self.assertEqual(response.status_code, 200)

    def test_library_style_redirect(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/library/mine')
        self.assertRedirects(response, '/library/bricks/title/mine/')

    def test_library_page(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/library/bricks/title/mine/')
        self.assertEqual(response.status_code, 200)

    def test_text_extraction(self):
        te = TextExtractor()
        result = te.extract(
            '<html><head><title>Hi</title></head><body><p>Some nice text.</p><script type="text/javascript">Script</script><p>More and nicer texts. Imnotinthebook.</p></body></html>')
        self.assertEqual(result, "Some nice text. More and nicer texts. Imnotinthebook. ")
        lists = te.get_word_lists(['nice', 'and'])
        self.assertListEqual(['text', 'nice', 'some', 'more', 'and'],
                             lists['all_words'],
                             'Did not extract correct set of words')
        self.assertListEqual(['imnotinthebook'],
                             lists['non_dict_words'],
                             'Did not recognize nonword')
        self.assertListEqual(['and', 'nice'],
                             lists['glossary_words'],
                             'Did not find glossary word')

    def test_parse_file(self):
        te = TextExtractor()
        zip = ZipFile('../content/nysed-penguins/nysed-penguins-1.epub')
        file = zip.open('OEBPS/content.xhtml')
        te.feed(file.read().decode('utf-8'))
        te.close()
        result = te.text
        self.assertRegex(result, "Penguins are funny birds")
        self.assertNotRegex(result, "Photo")
        word_lists = te.get_word_lists(['penguin'])
        #print(word_lists)
        self.assertTrue('penguin' in word_lists['all_words'], 'Parser didn\'t find a penguin in the penguins article')
        self.assertTrue('adelie' in word_lists['non_dict_words'], 'Parser didn\'t find Adelie as non-word')
        self.assertTrue('penguin' in word_lists['glossary_words'], 'Parser didn\'t find penguin in glossary words')
        self.assertFalse('1' in word_lists['all_words'], 'Parser didn\'t exclude number')
        self.assertFalse('1' in word_lists['non_dict_words'], 'Parser didn\'t exclude number')

    def test_manifest_picture_counting(self):
        file = '../content/nysed-penguins/nysed-penguins-1.epub'
        with open(file, 'rb') as f, dawn.open(f) as epub:
            pictures = 0
            for item in epub.manifest.values():
                if item.mimetype.startswith('image/'):
                    pictures += 1
        self.assertEqual(1, pictures, 'Should have found one picture in Penguins book')


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
        para = Paradata.objects.create(book=self.book, user=cuser, last_version = bv)
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
        self.assertEqual('testtest', pd.last_location)


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
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test period')
        assignments = BookAssignment.objects.all()
        self.assertEqual(1, len(assignments))

        # And remove it again
        response = self.client.post(reverse('share', kwargs={'pk': self.book.pk}), { })
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'test period')
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


class Customizations(TestCase):

    def setUp(self) -> None:
        self.site = Site.objects.create(name='test site', anon_id='test site')
        self.period1 = Period.objects.create(site=self.site, name='test period 1', anon_id='test period 1')
        self.period2 = Period.objects.create(site=self.site, name='test period 2', anon_id='test period 2')
        self.period3 = Period.objects.create(site=self.site, name='test period 3', anon_id='test period 3')
        teacher = User.objects.create_user(username="teacher", password="password1")
        self.teacher = ClusiveUser.objects.create(anon_id="T1", user=teacher, role='TE')
        self.teacher.periods.add(self.period1)
        self.teacher.save()

        student_1 = User.objects.create_user(username="student", password="password1")
        student_1.save()
        cuser = ClusiveUser.objects.create(anon_id="Student1", user=student_1, role='ST')
        cuser.save()

        self.book1 = Book.objects.create(owner=cuser, title='Book One', description='')
        self.book1.save()
        bv = BookVersion.objects.create(book=self.book1, sortOrder=0)
        bv.save()

        self.book2 = Book.objects.create(owner=cuser, title='Book Two', description='')
        self.book2.save()
        bv = BookVersion.objects.create(book=self.book2, sortOrder=0)
        bv.save()

        self.custom1 = Customization.objects.create(book=self.book1, owner=self.teacher)
        self.custom1.save()
        self.custom2 = Customization.objects.create(book=self.book2, owner=self.teacher)
        self.custom2.save()

        self.test_vocabulary = ['here', 'are', 'some', 'words']
        self.test_word = 'hello'
        self.custom_vocabulary_word = CustomVocabularyWord(customization=self.custom1, word=self.test_word)
        self.custom_vocabulary_word.save()

    def test_create(self):
        checks = [(self.custom1, self.book1, 1), (self.custom2, self.book2, 0)]
        for (customization, book, expected_custom_vocab_words) in checks:
            custom = Customization.objects.get(book=book)
            self.assertNotEqual(None, custom)
            self.assertEquals('Customization', customization.title)
            self.assertEquals(0, len(custom.periods.all()))
            self.assertEquals('', custom.question)
            self.assertEquals(expected_custom_vocab_words, len(custom.customvocabularyword_set.all()))

        # Check the newly created vocabulary list -- first() since there should
        # be only one at this point
        vocab = CustomVocabularyWord.objects.first()
        self.assertEquals(self.test_word, vocab.word)

        # Create another customization with a passed-in title
        test_title='Frankenstein custom vocabulary'
        custom = Customization.objects.create(book=self.book1, owner=self.teacher, title=test_title)
        custom.save()
        custom = Customization.objects.get(title=test_title)
        self.assertEquals(test_title, custom.title)

    def test_set_question(self):
        question = 'To be or not to be'
        self.custom1.question = question
        self.custom1.save()
        custom = Customization.objects.get(book=self.book1)
        self.assertEquals(question, custom.question)

    def test_set_vocabulary(self):
        # Create some CustomVocabularyWords and attach them to self.custom1
        # Customization
        for vocab_word in self.test_vocabulary:
            custom_vocab_word = CustomVocabularyWord.objects.create(word=vocab_word, customization=self.custom1)
            custom_vocab_word.save()

        # Find each `vocabulary` word as a CustomVocabularyWord in the first
        # Customization
        for vocab_word in self.test_vocabulary:
            custom_vocabulary = self.custom1.customvocabularyword_set.get(word=vocab_word)
            self.assertNotEquals(None, custom_vocabulary)

    def test_customization_word_list(self):
        # Test the `word_list` Customization property; should be empty
        self.assertEquals(0, len(self.custom2.word_list))

        # Store test vocabulary words into the second Customization
        for vocab_word in self.test_vocabulary:
            custom_vocab_word = CustomVocabularyWord.objects.create(word=vocab_word, customization=self.custom2)
            custom_vocab_word.save()

        # Test the `word_list` Customization property
        self.assertEquals(self.test_vocabulary, self.custom2.word_list)

    def test_periods(self):
        periods = [self.period1, self.period2]
        self.custom1.periods.set(periods)
        self.custom1.save()
        custom = Customization.objects.get(book=self.book1)
        custom_periods = custom.periods.all()
        self.assertNotEquals(0, len(custom_periods))
        self.assertTrue(self.period1 in custom_periods)
        self.assertTrue(self.period2 in custom_periods)
        self.assertFalse(self.period3 in custom_periods)


class ReadingLevels(TestCase):

    def setUp(self) -> None:
        # ARI scores (grades) that are within the ranges defined by ReadingLevel
        # and their expected minimum and maximum grades.
        self.ari_and_reading_levels = [
            { 'ari': 2, 'reading_level': ReadingLevel.EARLY_READER, 'expected_min': -math.inf, 'expected_max': 3},
            { 'ari': 4, 'reading_level': ReadingLevel.ELEMENTARY, 'expected_min': 4, 'expected_max': 5},
            { 'ari': 7, 'reading_level': ReadingLevel.MIDDLE_SCHOOL, 'expected_min': 6, 'expected_max': 8},
            { 'ari': 11, 'reading_level': ReadingLevel.HIGH_SCHOOL, 'expected_min': 9, 'expected_max': 12},
            { 'ari': 14, 'reading_level': ReadingLevel.ADVANCED, 'expected_min': 13, 'expected_max': math.inf},
        ]

    def test_min_grade(self):
        for grade in self.ari_and_reading_levels:
            self.assertEqual(grade['expected_min'], grade['reading_level'].min_grade)

    def test_max_grade(self):
        for grade in self.ari_and_reading_levels:
            self.assertEqual(grade['expected_max'], grade['reading_level'].max_grade)

    def test_for_grade(self):
        for ari_grade in self.ari_and_reading_levels:
            reading_level = ReadingLevel.for_grade(ari_grade['ari'])
            self.assertEquals(ari_grade['reading_level'], reading_level)

    def test_for_grade_range(self):
        # Test a range that gives a single category.
        expected = [ReadingLevel.HIGH_SCHOOL]
        actual = ReadingLevel.for_grade_range(9, 12)
        self.assertEqual(expected, actual)

        # Given a grade range of 2 through 7, expect a list of EARLY_READER,
        # ELEMENTARY, and MIDDLE_SCHOOL
        expected = [ReadingLevel.EARLY_READER, ReadingLevel.ELEMENTARY, ReadingLevel.MIDDLE_SCHOOL]
        actual = ReadingLevel.for_grade_range(2, 7)
        self.assertEqual(expected, actual)

        # Get all the reading levels using using lowest min and highest mas.
        expected = [rl for rl in ReadingLevel]
        actual = ReadingLevel.for_grade_range(-math.inf, math.inf)
        self.assertEqual(expected, actual)
