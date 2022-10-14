import logging

from django.contrib.auth.models import User

from roster.models import ClusiveUser
from simplification.util import WordnetSimplifier

logger = logging.getLogger(__name__)

from django.test import TestCase


class GlossaryTestCase(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        self.clusive_user = ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST')
        self.clusive_user.save()
        self.simplifier = WordnetSimplifier('en')

    def test_simplifies_words(self):
        info = self.simplifier.simplify_text('Thoroughly obscure verbiage', self.clusive_user, 100, include_full=True)
        self.assertEqual(3, info['word_count'])
        self.assertEqual(3, info['to_replace'])
        self.assertRegexpMatches(info['result'], r'Thoroughly.*obscure.*verbiage')
        self.assertRegexpMatches(info['result'], r'Good.*dark.*choice of words')

    def test_does_not_simplify_proper_nouns(self):
        info = self.simplifier.simplify_text('Jimmy Carter carted jimmies', self.clusive_user, 100, include_full=True)
        self.assertRegexpMatches(info['result'], r'<div class="text-alt-vertical">Jimmy Carter ')
        self.assertRegexpMatches(info['result'], r'aria-label="carted: alternate word">dragged')

        info = self.simplifier.simplify_text('Frank wrote a frank autobiography', self.clusive_user, 100, include_full=True)
        self.assertRegexpMatches(info['result'], r'<div class="text-alt-vertical">Frank')
        self.assertRegexpMatches(info['result'], r'aria-label="frank: alternate word">dog')
