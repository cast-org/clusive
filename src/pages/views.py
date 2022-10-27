import json
import logging
from datetime import date, timedelta
from os.path import exists

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Q, Prefetch, QuerySet
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, RedirectView
from django.views.generic.base import ContextMixin
from django.views.generic.edit import BaseCreateView

import flaticon.util
import nounproject.util
import translation
from assessment.forms import ClusiveRatingForm
from assessment.models import ClusiveRatingResponse, AffectiveUserTotal, ComprehensionCheckResponse, \
    AffectiveCheckResponse
from eventlog.models import Event
from eventlog.signals import star_rating_completed
from eventlog.views import EventMixin
from glossary.models import WordModel
from glossary.views import choose_words_to_cue
from library.models import Book, BookVersion, Paradata, Annotation, BookTrend, \
    Customization, BookAssignment
from roster.models import ClusiveUser, Period, Roles, UserStats, Preference
from tips.models import TipHistory, CTAHistory, CompletionType, TourList
from translation.util import TranslateApiManager

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
        data['theme_class'] = 'clusive-theme-' + Preference.get_theme_for_user(self.clusive_user)
        return data


class SettingsPageMixin(ContextMixin):
    """
    Set up context variables needed by the settings panel.
    This mixin should be added to all page views that include settings.
    """

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['translation_languages'] = TranslateApiManager.get_translate_language_list()
        return data


class PeriodChoiceMixin(ContextMixin):
    """
    Add this to Views that allow users to select one of their Periods to be active.
    Sets context variables "periods" (a list) and current_period (the selected one).
    If a kwarg called "period_id" is received, updates the current_period.
    """
    periods = None
    current_period = None

    def get_current_period(self, request, **kwargs):
        """Return the current period for this user, setting it if necessary."""
        if not self.current_period:
            clusive_user = request.clusive_user
            if self.periods is None:
                self.periods = clusive_user.periods.all().order_by(Lower('name'))
            if kwargs.get('period_id'):
                # User is setting a new period
                self.current_period = get_object_or_404(Period, pk=kwargs.get('period_id'))
                if self.current_period not in self.periods:
                    self.handle_no_permission()   # attempted to access a Period the user is not in
                logger.debug('Set current period to %s', self.current_period)
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
        return self.current_period

    def get(self, request, *args, **kwargs):
        self.get_current_period(request, **kwargs)
        result = super().get(request, *args, **kwargs)
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periods'] = self.periods
        context['current_period'] = self.current_period
        return context


class DashboardView(LoginRequiredMixin, ThemedPageMixin, SettingsPageMixin, EventMixin, PeriodChoiceMixin, TemplateView):
    template_name='pages/dashboard.html'

    def __init__(self):
        super().__init__()

    def get(self, request, *args, **kwargs):
        # Redirect administrators who mistakenly logged in with a link that goes here.
        if request.user.is_staff:
            return HttpResponseRedirect('/admin')

        self.clusive_user = request.clusive_user
        self.is_teacher = self.clusive_user.can_manage_periods
        self.is_guest = False if self.is_teacher else (self.request.clusive_user.role == 'GU')
        self.current_period = self.get_current_period(request, **kwargs)
        self.panels = dict()  # This will hold info on which panels are to be displayed.
        self.data = dict()    # This will hold panel-specific data
        self.dashboard_popular_view = self.clusive_user.dashboard_popular_view
        self.page_name = 'Dashboard'

        self.tip_shown = TipHistory.get_tip_to_show(self.clusive_user, page=self.page_name)
        self.tours = TourList(self.clusive_user, page=self.page_name)

        # Decision-making data
        user_stats = UserStats.objects.get(user=request.clusive_user)

        # Welcome panel
        self.panels['welcome'] = user_stats.reading_views == 0

        # Calls to Action
        cta_name = None
        if request.GET.get('cta'):
            # Manual override, for testing. Named CTA will be shown, but not recorded in history.
            cta_name = request.GET.get('cta')
        else:
            histories = CTAHistory.available_ctas(user=self.clusive_user, page='Dashboard')
            if histories:
                logger.debug('CTAs: %s', repr(histories))
                histories[0].show()  # Record the fact that it was displayed.
                cta_name = histories[0].type.name
        if cta_name:
            self.panels['cta'] = True
            self.data['cta'] = {
                'type': cta_name,
            }
            if cta_name == 'star_rating':
                self.data['cta']['form'] = ClusiveRatingForm(initial={'star_rating': 0})
        else:
            self.panels['cta'] = False

        # Affect panel (for student)
        self.panels['affect'] = not self.is_teacher and user_stats.reading_views > 0
        if self.panels['affect']:
            totals = AffectiveUserTotal.objects.filter(user=request.clusive_user).first()
            self.data['affect'] = {
                'totals':  AffectiveUserTotal.scale_values(totals),
                'empty': totals is None,
            }

        # Class Affect panel (for parent/teacher)
        self.panels['class_affect'] = self.is_teacher and self.current_period
        if self.panels['class_affect']:
            sa = AffectiveUserTotal.objects.filter(user__periods=self.current_period, user__role=Roles.STUDENT)
            scaled = AffectiveUserTotal.aggregate_and_scale(sa)
            logger.debug('scaled: %s', scaled)
            self.data['class_affect'] = {
                'totals': scaled,
                'empty': not any([item['value'] for item in scaled]),
            }
            logger.debug("Scaled: %s", scaled)

        # Star results panel
        self.panels['star_results'] = self.should_show_star_results(request)
        if self.panels['star_results']:
            self.data['star_results'] = {
                'form': ClusiveRatingForm(initial={'star_rating': self.star_rating.star_rating}),
                'results': ClusiveRatingResponse.get_graphable_results(),
            }

        # Popular Reads panel
        # Tabbed panel with Assigned, Recent, and Popular readings.
        # Tabs are AJAX updated via PopularReadsPanelView()
        self.panels['popular_reads'] = True

        # Check for persistent choice
        if self.dashboard_popular_view != '':
            self.data['popular_reads'] = get_readings_data(self.clusive_user, self.dashboard_popular_view, self.current_period)
        if self.dashboard_popular_view == '' or self.data['popular_reads']['view'] == '':
            # Default is Assigned except for students without a classroom
            if self.clusive_user.role == Roles.STUDENT and not self.current_period:
                self.data['popular_reads'] = get_recent_reads_data(self.clusive_user)
            else:
                self.data['popular_reads'] = get_assigned_reads_data(self.clusive_user)

        # Student Activity panel
        self.panels['student_activity'] = self.is_teacher
        sa_days = self.clusive_user.student_activity_days
        sa_sort = self.clusive_user.student_activity_sort
        if self.panels['student_activity']:
            self.data['student_activity'] = {
                'days': sa_days,
                'sort': sa_sort,
                'reading_data':
                    Paradata.reading_data_for_period(self.current_period, days=sa_days, sort=sa_sort)
                    if self.current_period else None
            }

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_teacher'] = self.is_teacher
        context['is_guest'] = self.is_guest
        context['period_name'] = self.current_period.name if self.current_period else None
        context['query'] = None
        context['panels'] = self.panels
        context['data'] = self.data
        context['clusive_user'] = self.clusive_user
        # 'tour' is a special case and uses the older tooltip functionality
        context['tip_name'] = 'tour' if self.tip_shown and self.tip_shown.name == 'tour' else None # tour tooltip
        context['tip_shown'] = self.tip_shown.name if self.tip_shown and self.tip_shown.name != 'tour' else None # Singleton tour item
        context['tours'] = self.tours
        context['has_teacher_resource'] = True
        context['page_name'] = self.page_name
        return context

    def should_show_star_results(self, request):
        # Put 'starresults=1' in URL for debugging
        if request.GET.get('starresults'):
            return True

        # Otherwise, only shown via AJAX request after rating.
        return False

    def configure_event(self, event: Event):
        event.page = 'Dashboard'
        event.tip_type = self.tip_shown


class PopularReadsPanelView(LoginRequiredMixin, TemplateView):
    """Used for AJAX request to switch between Recent, Popular, and Assigned views of the 'popular readings' panel."""
    template_name = 'pages/partial/dashboard_panel_popular_reads_data.html'

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.view = kwargs['view']
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_period = self.clusive_user.current_period
        is_teacher = self.clusive_user.can_manage_periods
        is_guest = self.clusive_user.role == 'GU'

        readings = get_readings_data(self.clusive_user, self.view, current_period)

        # Set defaults for next time
        user_changed = False
        if self.clusive_user.dashboard_popular_view != self.view:
            self.clusive_user.dashboard_popular_view = self.view
            user_changed = True
        if user_changed:
            self.clusive_user.save()

        context.update({
            'is_teacher': is_teacher,
            'is_guest': is_guest,
            'current_period': current_period,
            'period_name': current_period.name if current_period else None,
            'query': None,
            'data': readings,
        })
        return context


def get_recent_reads_data(clusive_user):
    """Return most recently read items for the given user"""
    # Select latest 4 so we can tell if the 3 displayed is all, or just some, of the user's reads.
    recent = Paradata.latest_for_user(clusive_user).prefetch_related('book')[:4]
    truncated = len(recent) > 3
    items = []
    for para in recent[:3]:
        book = para.book
        # Paradata is expected to be provided this way for "starred" support
        book.paradata_list = [para]
        items.append({'book': book})

    return {
        'view': 'recent',
        'all': items,
        'is_truncated': truncated,
    }

def get_readings_data(clusive_user, view, current_period):
    if view == 'assigned':
        readings = get_assigned_reads_data(clusive_user)
    elif view == 'recent':
        readings = get_recent_reads_data(clusive_user)
    elif view == 'popular':
        readings = get_popular_reads_data(clusive_user, current_period)
    else:
        # raise NotImplementedError('No such view')
        readings = {
            'view': ''
        }
    return readings

def get_assigned_reads_data(clusive_user: ClusiveUser):
    """
    Return the most recent assignments in the user's current period.
    For users without a current period, returns the featured book(s) (eg, Clues to Clusive).
    """
    if clusive_user.role == Roles.GUEST:
        featured = Book.get_featured_books()
        # Attach paradata (for 'starred' support)
        paradata_query = Paradata.objects.filter(user=clusive_user)
        featured = featured.prefetch_related(Prefetch('paradata_set', queryset=paradata_query, to_attr='paradata_list'))
        items = [{'book': b} for b in featured[:3]]
        return {
            'view': 'assigned',
            'all': items,
            'is_truncated': False,
        }
    # Select latest 4 so we can tell if the 3 displayed is all, or just some, of the assignments.
    # Attach paradata (for 'starred' support)
    paradata_query = Paradata.objects.filter(user=clusive_user)
    assignments = BookAssignment.recent_assigned(clusive_user.current_period)\
        .prefetch_related('book')\
        .prefetch_related(Prefetch('book__paradata_set', queryset=paradata_query, to_attr='paradata_list'))[:4]
    truncated = len(assignments) > 3
    items = [{'book': ba.book} for ba in assignments[:3]]
    if clusive_user.can_manage_periods:
        for item in items:
            item['user_count'] = BookTrend.user_count_for_assigned_book(item['book'], clusive_user.current_period)
            add_teacher_details(item, clusive_user)

    return {
        'view': 'assigned',
        'all': items,
        'is_truncated': truncated,
    }


def get_popular_reads_data(clusive_user: ClusiveUser, current_period: Period):
    # Gather data about books that are popular for dashboard view
    trend_query = BookTrend.top_trends(current_period)
    logger.debug('gprd %s', trend_query)
    if current_period == None:
        # If user has no Period (eg, a guest) 'trends' is a query across the top trends in any Period.
        # We don't want to retrieve this huge dataset fully, but just walk through the top items
        # to find the books that feature there as popular.
        trends = unique_books(trend_query, clusive_user, 4)
        logger.debug('gprd unique %s', trends)
    else:
        if clusive_user.can_manage_periods:
            # Teachers are allowed to see what's popular even if they cannot access the book themselves.
            trends = trend_query[:4]
        else:
            trends = cull_unauthorized_from_readings(trend_query, clusive_user)[:4]

    is_truncated = len(trends) > 3

    trend_data = [{'trend': t} for t in trends[:3]]
    for td in trend_data:
        t = td['trend']
        book = td['trend'].book
        td['book'] = book
        td['user_count'] = t.user_count
        book.paradata_list = list(Paradata.objects.filter(book=book, user=clusive_user))
        if clusive_user.can_manage_periods:
            add_teacher_details(td, clusive_user)

    return {
        'view': 'popular',
        'all': trend_data,
        'is_truncated': is_truncated,
    }


def add_teacher_details(item: dict, clusive_user: ClusiveUser):
    """
    Add additional information to the given dict for teacher-side display of the library card.
    :param item:
    :param clusive_user:
    :return:
    """
    periods = list(clusive_user.periods.all())
    item['book'].add_teacher_extra_info(periods)
    # Check if there is a customization for the current period.
    for c in item['book'].custom_list:
        if clusive_user.current_period in list(c.periods.all()):
            item['customization'] = c
    # Get comp check statistics
    item['comp_check'] = ComprehensionCheckResponse.get_counts(item['book'], clusive_user.current_period)
    item['unauthorized'] = not item['book'].is_visible_to(clusive_user)


def unique_books(trends: QuerySet, clusive_user: ClusiveUser, count: int):
    unique_book_trends = []
    books = set()  # track books already seen
    for trend in trends.iterator(chunk_size=10):
        logger.debug('Checkin trend: %s', trend)
        if trend.book not in books:
            books.add(trend.book)
            if trend.book.is_visible_to(clusive_user):
                unique_book_trends.append(trend)
                if len(unique_book_trends) == count:
                    break
    return unique_book_trends


def cull_unauthorized_from_readings(readings, clusive_user):
    """
    Check the given list of `readings` and return a new list of readings
    containing only the books that the `clusive_user` is authorized to view.
    Required:  each item in the `readings` has a `book` property that is an
    instance of a `library.models.Book`.
    """
    results = []
    # The loop assumes the `readings` are ordered and uses `results.append()` to
    # maintain that order.
    for reading in readings:
        if reading.book.is_visible_to(clusive_user):
            results.append(reading)
        else:
            logger.debug('Culling %s from Dashboard view as unauthorized for %s',
                reading.book.title,
                clusive_user.user.username)
    return results


class DashboardActivityPanelView(TemplateView):
    """Shows just the activity panel, for AJAX updates"""
    template_name = 'pages/partial/dashboard_panel_student_activity.html'

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.current_period = request.clusive_user.current_period

        if 'days' in kwargs:
            self.days = kwargs.get('days')
            logger.debug('Setting student activity days = %d', self.days)
            self.clusive_user.student_activity_days = self.days
            self.clusive_user.save()
        else:
            self.days = self.clusive_user.student_activity_days

        if 'sort' in kwargs:
            self.sort = kwargs.get('sort')
            logger.debug('Setting student activity sort = %s', self.sort)
            self.clusive_user.student_activity_sort = self.sort
            self.clusive_user.save()
        else:
            self.sort = self.clusive_user.student_activity_sort

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['data'] = {
            'days': self.days,
            'sort': self.sort,
            'reading_data': Paradata.reading_data_for_period(self.current_period, days=self.days, sort=self.sort),
        }
        return context


class DashboardActivityDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'shared/partial/modal_student_activity_detail.html'

    def get_context_data(self, **kwargs):
        user_id = kwargs['user_id']
        book_id = kwargs['book_id']
        data = super().get_context_data(**kwargs)

        try:
            clusive_user = ClusiveUser.objects.get(pk=user_id)
            data['clusive_user'] = clusive_user
            book = Book.objects.get(pk=book_id)
            data['book'] = book
            data['book_has_versions'] = book.versions.count() > 1

            paras = Paradata.objects.filter(user=clusive_user, book=book)
            # Annotate with the time total from the last week
            start_date = date.today()-timedelta(days=7)
            paras = paras.annotate(recent_time=Sum('paradatadaily__total_time',
                                                           filter=Q(paradatadaily__date__gt=start_date)))
            paradata = paras[0]
            data['paradata'] = paradata
            if paradata.first_version and paradata.first_version != paradata.last_version:
                data['version_switched'] = True

            # Affect and Comp check
            affect_checks = AffectiveCheckResponse.objects.filter(user=clusive_user, book=book)
            if affect_checks:
                data['affect_check'] = affect_checks[0]
            comp_checks = ComprehensionCheckResponse.objects.filter(user=clusive_user, book=book)
            if comp_checks:
                data['comp_check'] = comp_checks[0]

            # Highlights and notes
            data['highlight_count'] = Annotation.objects.filter(bookVersion__book=book, user=clusive_user, dateDeleted=None).count()
            data['note_count'] = Annotation.objects.filter(bookVersion__book=book, user=clusive_user, dateDeleted=None,
                                                           note__isnull=False).exclude(note='').count()

            return data
        except ClusiveUser.DoesNotExist:
            logger.error('No clusive user %d', user_id)
            raise Http404('No such user')
        except Book.DoesNotExist:
            logger.error('No such book %d', book_id)
            raise Http404('No such book')


class SetStarRatingView(LoginRequiredMixin, BaseCreateView):
    form_class = ClusiveRatingForm
    success_url = reverse_lazy('star_rating_results')

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # Save rating
        self.object = form.save(commit=False)
        self.object.user = self.request.clusive_user
        self.object.save()
        # Update Call To Action
        CTAHistory.register_action(user=self.request.clusive_user,
                                   cta_name='star_rating', completion_type=CompletionType.TAKEN)
        # Log event
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
        context = super().get_context_data(**kwargs)
        initial = {'star_rating': self.rating.star_rating} if self.rating else None
        context['data'] = {
            'form': ClusiveRatingForm(initial=initial),
            'results': self.results,
        }
        return context


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
            sort = clusive_user.library_sort
            if view == 'period' and clusive_user.current_period:
                return reverse('library', kwargs = {
                    'style': style,
                    'sort': sort,
                    'view': 'period',
                    'period_id': clusive_user.current_period.id
                })
            else:
                return reverse('library', kwargs = {
                    'style': style,
                    'sort': sort,
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


class ReaderView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, TemplateView):
    """Reader page showing a page of a book"""
    template_name = 'pages/reader.html'

    def get(self, request, *args, **kwargs):
        resource_identifier = kwargs.get('resource_id')
        book_id = kwargs.get('book_id')
        version = kwargs.get('version') or 0
        if resource_identifier:
            book = Book.objects.get(resource_identifier=resource_identifier)
        else:
            book = Book.objects.get(pk=book_id)
        self.page_name = 'ResourceReading' if book.is_educator_resource else 'Reading'

        if not book.is_visible_to(request.clusive_user):
            raise PermissionDenied()
        versions = book.versions.all()
        clusive_user = request.clusive_user
        self.book_version = versions[version]
        self.book = book
        annotationList = Annotation.get_list(user=clusive_user, book_version=self.book_version)
        cuelist_map = choose_words_to_cue(book_version=self.book_version, user=clusive_user)
        # Make into format that R2D2BC wants for "definitions"
        cuelist = [{ 'order': i, 'result': 1, 'terms': terms } for i, terms in enumerate(cuelist_map.values())]
        logger.debug('Cuelist: %s', repr(cuelist))
        pdata = Paradata.record_view(book, version, clusive_user)
        # See if user wants the cues to be initially shown or not
        hide_cues = not Preference.get_glossary_pref_for_user(clusive_user)

        # See if there's a Tip that should be shown
        self.tip_shown = TipHistory.get_tip_to_show(clusive_user, page=self.page_name, version_count=len(versions))
        self.tours = TourList(clusive_user, page=self.page_name, version_count=len(versions))

        # See if there's a custom question
        customizations = Customization.objects.filter(book=book, periods=clusive_user.current_period) \
            if clusive_user.current_period else None
        logger.debug('Customization: %s', customizations)

        if exists(self.book_version.storage_dir + '/positions.json'):
            positions_path = self.book_version.positions_path
            weight_path = self.book_version.weight_path
            logger.debug('Positions: %s, Weight: %s', positions_path, weight_path)
        else:
            positions_path = weight_path = False
            logger.debug('No pre-calculated positions or weight')

        self.extra_context = {
            'clusive_user': clusive_user,
            'pub': book,
            'version_number': self.book_version.sortOrder,
            'version_id': self.book_version.id,
            'version_count': len(versions),
            'manifest_path': self.book_version.manifest_path,
            'positions_path': positions_path,
            'weight_path': weight_path,
            'last_position': pdata.last_location or "null",
            'annotations': annotationList,
            'cuelist': json.dumps(cuelist),
            'hide_cues': hide_cues,
            'tip_name': None,
            'tip_shown': self.tip_shown.name if self.tip_shown else None,
            'tours': self.tours,
            'has_teacher_resource': True,
            'page_name': self.page_name,
            'customization': customizations[0] if customizations else None,
            'starred': pdata.starred,
            'book_id': book.id,
            'simplification_tool': clusive_user.transform_tool,
            'simplification_show_translate': translation.util.translation_is_configured(),
            'simplification_show_pictures': flaticon.util.flaticon_is_configured() or nounproject.util.nounproject_is_configured(),
        }
        return super().get(request, *args, **kwargs)

    def configure_event(self, event: Event):
        event.page = self.page_name
        event.book_version_id = self.book_version.id
        event.book_id = self.book.id
        event.tip_type = self.tip_shown


class WordBankView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, TemplateView):
    template_name = 'pages/wordbank.html'

    def get(self, request, *args, **kwargs):
        # Check for Tip
        clusive_user = request.clusive_user
        tip_shown = TipHistory.get_tip_to_show(clusive_user, page='Wordbank')
        tours = TourList(clusive_user, page='Wordbank')

        self.extra_context = {
            'words': WordModel.objects.filter(user=request.clusive_user, interest__gt=0).order_by('word'),
            'clusive_user': clusive_user,
            'tip_name': None,
            'tip_shown': tip_shown.name if tip_shown else None,
            'tours': tours,
            'has_teacher_resource': False,
        }
        return super().get(request, *args, **kwargs)

    def configure_event(self, event: Event):
        event.page = 'Wordbank'


class AboutView(TemplateView):
    template_name = 'pages/about.html'


class PrivacyView(TemplateView):
    template_name = 'pages/privacy.html'


class DebugView(TemplateView):
    template_name = 'pages/debug.html'
