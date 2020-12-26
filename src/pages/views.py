import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView, RedirectView

from eventlog.models import Event
from eventlog.views import EventMixin
from glossary.models import WordModel
from library.models import Book, BookVersion, Paradata, Annotation
from roster.models import ClusiveUser
from tips.models import TipHistory

logger = logging.getLogger(__name__)

class ReaderIndexView(LoginRequiredMixin,RedirectView):
    """This is the 'home page', currently just redirects to the user's default library view."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_staff:
            logger.debug("Staff login")
            return 'admin'
        else:
            clusive_user : ClusiveUser
            clusive_user = get_object_or_404(ClusiveUser, user=self.request.user)
            view = clusive_user.library_view
            style = clusive_user.library_style
            if view == 'period' and clusive_user.current_period:
                return reverse('library', kwargs = {
                    'style': style,
                    'view': 'period',
                    'period_id': clusive_user.current_period.id
                })
            else:
                return reverse('library', kwargs = {
                    'style': style,
                    'view': view
                })


class ReaderChooseVersionView(RedirectView):
    """Determine appropriate version of book to show, and redirect to it. """
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        book_id = kwargs.get('book_id')
        versions = BookVersion.objects.filter(book__pk=book_id)
        v = None
        if len(versions) == 1:
            # Shortcut: only one version exists, go there.
            v = 0
        else:
            clusive_user = get_object_or_404(ClusiveUser, user=self.request.user)
            try:
                paradata = Paradata.objects.get(book__pk=book_id, user=clusive_user)
                # Return to the last version this user viewed.
                v = paradata.lastVersion.sortOrder
                logger.debug('Returning to last version viewed (%d)', v)
            except:
                # No previous view - determine where to send the user based on vocabulary.
                logger.debug('New book for this user, choosing from versions...')
                # Compute an estimate of the fraction of words in each version that the user does not know
                # This is attached to the versions as "novel_frac".
                for bv in versions:
                    logger.debug('Considering version: %s', bv)
                    if bv.sortOrder==0:
                        words = bv.all_word_list
                        wordcount = len(words)
                        logger.debug('  Word count: %d', wordcount)
                        user_words = WordModel.objects.filter(user=clusive_user, word__in=words)
                        logger.debug('  Have ratings for %d', len(user_words))
                        not_known = len([u for u in user_words if (u.knowledge_est() or 3)<2])
                        bv.novel_frac = not_known/wordcount
                        logger.debug('  %d words have not-known ratings, so novel_frac = %f', not_known, bv.novel_frac)
                    else:
                        words = bv.all_word_list
                        prev_version = versions[bv.sortOrder - 1]
                        new_words = bv.new_word_list
                        logger.debug("  New words in this version (%d): %s", len(new_words), new_words)
                        user_words = WordModel.objects.filter(user=clusive_user, word__in=new_words)
                        user_words = [u for u in user_words if u.knowledge_est()!=None]
                        if (user_words):
                            not_known_count = len([u for u in user_words if u.knowledge_est()<2])
                            new_novel_frac = not_known_count/len(user_words)
                            logger.debug('  Have ratings for %d; of those %d are not known (%f)',
                                         len(user_words), not_known_count, new_novel_frac)
                            common_word_count = len(words)-len(new_words)
                            bv.novel_frac = (common_word_count*prev_version.novel_frac + len(new_words)*new_novel_frac)/len(words)
                            logger.debug('  Assuming %f of new words are NK, and %f of old words are NK, novel_frac = %f',
                                         new_novel_frac, prev_version.novel_frac, bv.novel_frac)
                        else:
                            # For now assume it's the same as the previous version, I guess.
                            bv.novel_frac = prev_version.novel_frac
                            logger.debug('  No ratings for these words. Defaulting to same novel_frac as last version: %f.',
                                         bv.novel_frac)
                # Choose highest version with novel_frac below a threshhold.
                threshhold = .01
                v=len(versions)-1
                while v>0 and versions[v].novel_frac > threshhold:
                    v -= 1
                logger.debug("Chose version %d: last one under threshhold of %f", v, threshhold)
        kwargs['version'] = v
        return super().get_redirect_url(*args, **kwargs)


class ReaderView(LoginRequiredMixin, EventMixin, TemplateView):
    """Reader page showing a page of a book"""
    template_name = 'pages/reader.html'

    def get(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        version = kwargs.get('version')
        book = Book.objects.get(pk=book_id)
        versions = book.versions.all()
        clusive_user = request.clusive_user
        self.book_version = versions[version]
        annotationList = Annotation.get_list(user=clusive_user, book_version=self.book_version)
        pdata = Paradata.record_view(book, version, clusive_user)

        # See if there's a Tip that should be shown
        available = TipHistory.available_tips(clusive_user)
        if available:
            first_available = available[0]
            logger.debug('Displaying tip: %s', first_available)
            first_available.show()
            self.tip_shown = first_available.type
            tip_name = self.tip_shown.name
        else:
            self.tip_shown = None
            tip_name = None

        self.extra_context = {
            'pub': book,
            'version_count': len(versions),
            'manifest_path': self.book_version.manifest_path,
            'last_position': pdata.lastLocation or "null",
            'annotations': annotationList,
            'tip_name': tip_name,
        }
        return super().get(request, *args, **kwargs)

    def configure_event(self, event: Event):
        event.page = 'Reading'
        event.book_version_id = self.book_version.id
        event.tip_type = self.tip_shown


class WordBankView(LoginRequiredMixin, EventMixin, TemplateView):
    template_name = 'pages/wordbank.html'

    def get(self, request, *args, **kwargs):
        self.extra_context = {
            'words': WordModel.objects.filter(user=request.clusive_user, interest__gt=0).order_by('word')
        }
        return super().get(request, *args, **kwargs)

    def configure_event(self, event: Event):
        event.page = 'Wordbank'
