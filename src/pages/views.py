import logging
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, RedirectView, CreateView
from django.views.generic.base import ContextMixin
from django.views.generic.edit import BaseCreateView

from assessment.forms import ClusiveRatingForm
from assessment.models import ClusiveRatingResponse, StarRatingScale
from eventlog.models import Event
from eventlog.signals import star_rating_completed
from eventlog.views import EventMixin
from glossary.models import WordModel
from library.models import Book, BookVersion, Paradata, Annotation
from roster.models import ClusiveUser, Period, Roles, UserStats, Preference
from tips.models import TipHistory

logger = logging.getLogger(__name__)


class ThemedPageMixin(ContextMixin):
    """
    Set up for the correct color theme to be applied to the page.
    This mixin provides a theme_class context variable to the view, according to user's preference,
    which is used by base.html to set a class attribute on the body tag.
    """

    def dispatch(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['theme_class'] = 'clusive-theme-' + Preference.get_theme_for_user(self.clusive_user).value
        return data


class PeriodChoiceMixin(ContextMixin):
    """
    Add this to Views that allow users to select one of their Periods to be active.
    Sets context variables "periods" (a list) and current_period (the selected one).
    If a kwarg called "period_id" is received, updates the current_period.
    """
    periods = None
    current_period = None

    def get(self, request, *args, **kwargs):
        clusive_user = request.clusive_user
        if self.periods is None:
            self.periods = clusive_user.periods.all()
        if kwargs.get('period_id'):
            # User is setting a new period
            self.current_period = get_object_or_404(Period, pk=kwargs.get('period_id'))
            if self.current_period not in self.periods:
                self.handle_no_permission()   # attempted to access a Period the user is not in
        if self.current_period is None:
            # Set user's default Period
            if clusive_user.current_period:
                self.current_period = clusive_user.current_period
            elif self.periods:
                self.current_period = self.periods[0]
        if self.current_period != clusive_user.current_period and self.current_period != None:
            # Update user's default period to current
            clusive_user.current_period = self.current_period
            clusive_user.save()
        result = super().get(request, *args, **kwargs)
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periods'] = self.periods
        context['current_period'] = self.current_period
        return context


class DashboardView(LoginRequiredMixin, ThemedPageMixin, EventMixin, PeriodChoiceMixin, TemplateView):
    template_name='pages/dashboard.html'

    def __init__(self):
        super().__init__()

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user

        # Data for star rating panel
        self.star_rating = ClusiveRatingResponse.objects.filter(user=request.clusive_user).order_by('-created').first()
        self.show_star_rating = self.should_show_star_rating(request)
        self.show_star_results = self.should_show_star_results(request)
        if self.show_star_rating:
            self.star_form = ClusiveRatingForm(initial={'star_rating': 0})
            self.star_results = None
        elif self.show_star_results:
            self.star_results = ClusiveRatingResponse.get_graphable_results()
            self.star_form = ClusiveRatingForm(initial={'star_rating': self.star_rating.star_rating})
        else:
            self.star_results = None
            self.star_form = None

        # Data for "recent reads" panel
        self.last_reads = Paradata.latest_for_user(request.clusive_user)[:3]
        if not self.last_reads or len(self.last_reads) < 3:
            # Add featured books to the list
            features = list(Book.get_featured_books()[:3])
            # Remove any featured books that are in the user's last-read list.
            for para in self.last_reads:
                if para.book in features:
                    features.remove(para.book)
            self.featured = features
        else:
            self.featured = []
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['show_star_rating'] = self.show_star_rating
        data['star_form'] = self.star_form
        data['show_star_results'] = self.show_star_results
        data['star_results'] = self.star_results
        data['last_reads'] = self.last_reads
        data['featured'] = self.featured
        data['query'] = None
        if self.clusive_user.can_manage_periods:
            data['days'] = 0
            if self.current_period != None:
                data['reading_data'] = Paradata.reading_data_for_period(self.current_period, days=0)
        return data

    def should_show_star_rating(self, request):
        # Put 'starpanel=1' in URL for debugging
        if request.GET.get('starpanel'):
            return True

        # If already rated, don't show again.
        if self.star_rating:
            return False

        # Guests can't vote
        if request.clusive_user.role == Roles.GUEST:
            return False

        # Otherwise, show if user has 3+ logins or 1+ hours active use.
        user_stats = UserStats.objects.get(user=request.clusive_user)
        if user_stats.logins > 3:
            logger.debug('Requesting star rating: logins=%d', user_stats.logins)
            return True
        if user_stats.active_duration and user_stats.active_duration > timedelta(hours=1):
            logger.debug('Requesting star rating: active_duration=%d', user_stats.active_duration)
            return True
        return False

    def should_show_star_results(self, request):
        # Put 'starresults=1' in URL for debugging
        if request.GET.get('starresults'):
            return True

        # Otherwise, only shown via AJAX request after rating.
        return False

    def configure_event(self, event: Event):
        event.page = 'Dashboard'


class DashboardActivityPanelView(TemplateView):
    template_name = 'pages/partial/dashboard_panel_student_activity.html'

    def get(self, request, *args, **kwargs):
        self.current_period = request.clusive_user.current_period
        self.days = kwargs['days']
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['days'] = self.days
        data['reading_data'] = Paradata.reading_data_for_period(self.current_period, days=self.days)
        return data


class SetStarRatingView(LoginRequiredMixin, BaseCreateView):
    form_class = ClusiveRatingForm
    template_name = 'pages/partial/dashboard_panel_star_rating.html'
    success_url = reverse_lazy('star_rating_results')

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.clusive_user
        self.object.save()
        question = 'How would you rate your experience with Clusive so far?'
        star_rating_completed.send(SetStarRatingView.__class__, request=self.request,
                                   question=question, answer=self.object.star_rating)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        logger.debug('Form invalid: %s', form)
        return super().form_invalid(form)


class StarRatingResultsView(LoginRequiredMixin,TemplateView):
    """Display just the star rating panel. Used for AJAX request"""
    template_name = 'pages/partial/dashboard_panel_star_rating_results.html'

    def dispatch(self, request, *args, **kwargs):
        self.rating = ClusiveRatingResponse.objects.filter(user=request.clusive_user).order_by('-created').first()
        self.results = ClusiveRatingResponse.get_graphable_results()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        initial = {'star_rating': self.rating.star_rating} if self.rating else None
        self.star_form = ClusiveRatingForm(initial=initial)
        data['star_form'] = self.star_form
        data['star_results'] = self.results
        return data


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
                    'sort': 'title',   # FIXME
                    'view': 'period',
                    'period_id': clusive_user.current_period.id
                })
            else:
                return reverse('library', kwargs = {
                    'style': style,
                    'sort': 'title',  # FIXME
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
                v = paradata.last_version.sortOrder
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


class ReaderView(LoginRequiredMixin, EventMixin, ThemedPageMixin, TemplateView):
    """Reader page showing a page of a book"""
    template_name = 'pages/reader.html'
    page_name = 'Reading'

    def get(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        version = kwargs.get('version')
        book = Book.objects.get(pk=book_id)
        if not book.is_visible_to(request.clusive_user):
            raise PermissionDenied()
        versions = book.versions.all()
        clusive_user = request.clusive_user
        self.book_version = versions[version]
        self.book = book
        annotationList = Annotation.get_list(user=clusive_user, book_version=self.book_version)
        pdata = Paradata.record_view(book, version, clusive_user)

        # See if there's a Tip that should be shown
        available = TipHistory.available_tips(clusive_user, page=self.page_name, version_count=len(versions))
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
            'version_id': self.book_version.id,
            'version_count': len(versions),
            'manifest_path': self.book_version.manifest_path,
            'last_position': pdata.last_location or "null",
            'annotations': annotationList,
            'tip_name': tip_name,
        }
        return super().get(request, *args, **kwargs)

    def configure_event(self, event: Event):
        event.page = self.page_name
        event.book_version_id = self.book_version.id
        event.book_id = self.book.id
        event.tip_type = self.tip_shown


class WordBankView(LoginRequiredMixin, EventMixin, ThemedPageMixin, TemplateView):
    template_name = 'pages/wordbank.html'

    def get(self, request, *args, **kwargs):
        self.extra_context = {
            'words': WordModel.objects.filter(user=request.clusive_user, interest__gt=0).order_by('word')
        }
        return super().get(request, *args, **kwargs)

    def configure_event(self, event: Event):
        event.page = 'Wordbank'


class DebugView(TemplateView):
    template_name = 'pages/debug.html'
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PrivacyView(TemplateView):
    template_name = 'pages/privacy.html'
