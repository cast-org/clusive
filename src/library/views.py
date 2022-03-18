import imghdr
import json
import logging
import os
import shutil
from tempfile import mkstemp
from urllib.parse import urlencode

import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet, Prefetch
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, FormView, UpdateView, TemplateView, RedirectView

from eventlog.models import Event
from eventlog.signals import annotation_action, book_starred
from eventlog.views import EventMixin
from library.forms import UploadForm, MetadataForm, ShareForm, SearchForm, BookshareSearchForm, EditCustomizationForm
from library.models import Paradata, Book, Annotation, BookVersion, BookAssignment, Subject, BookTrend, Customization, \
    CustomVocabularyWord
from library.parsing import scan_book, convert_and_unpack_docx_file, unpack_epub_file
from oauth2.bookshare.views import BookshareOAuth2Adapter, has_bookshare_account, \
    is_bookshare_connected, get_access_keys, is_organizational_account, get_organization_name, \
    get_organization_members
from pages.views import ThemedPageMixin, SettingsPageMixin
from roster.models import ClusiveUser, Period, LibraryViews, LibraryStyles,\
    BookshareOrgUserAccount, check_valid_choice
from tips.models import TipHistory

logger = logging.getLogger(__name__)

# The library page requires a lot of parameters, which interact in rather complex ways.
# Here's a summary.  It is a sort-of hierarchy, in that changing parameters higher on this list
# can reset parameters that are lower on the list, but the effects never go in the opposite direction.
#
# STYLE (which should perhaps have been called "layout"): [bricks, grid, list]
#   This is the first part of the URL
#   Changing the style leaves all the other parameters unchanged.
#   The links in the style menu therefore have a JS helper to add the current filter and page to the URL.
#   The ClusiveUser model holds a default for style.
# VIEW (which should perhaps have been called "collection"): [public, mine, starred, or period]
#   This is the third part of the library URL
#   If view is "period", there is a fourth part of the URL which is the specific period being viewed.
#   Changing the view resets QUERY, FILTER, and PAGE to their defaults.
#   Links in the view menu are just URLs.
#   The ClusiveUser model holds a default for view & period.
# SORT: [title, author]
#   This is the second part of the URL
#   Changing the sort resets the PAGE to its default.
#   The links in the sort menu have a JS helper to add the current filter to the URL.
# QUERY: [any search string typed in by the user]
#   This is represented as a query= parameter in the URL
#   Changing the query resets the FILTER and PAGE to their defaults.
#   Query is changed by the search form, which does a simple GET.
# FILTER: [sets of keywords for "subject" and for "words"]
#   This is represented as subject= and words= URL parameters
#   Changing the filter resets the PAGE to its default.
#   The filter form has AJAX functionality to live-update the contents of the page when checkboxes are changed.
# PAGE: [1-n]
#   This is represented as a page= paramter in the URL.
#   Changing the page leaves all the other parameters unchanged.
#   Page links are implemented with AJAX.
#
# Summary of what resets what:
# STYLE:
# VIEW:  query, filter, page
# SORT:                 page
# QUERY:        filter, page
# FILTER:               page
# PAGE:

class LibraryDataView(LoginRequiredMixin, ListView):
    """
    Just the list of cards and navigation bar part of the library page.
    Used for AJAX updates of the library page.
    """
    template_name = 'library/partial/library_data.html'
    paginate_by = 21
    paginate_orphans = 3

    style = None
    view = 'public'
    view_name = None  # User-visible name for the current view
    period = None
    query = None
    subjects = None

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.style = kwargs.get('style')
        self.sort = kwargs.get('sort')
        self.view = kwargs.get('view')
        self.query = request.GET.get('query')

        self.show_assignments = self.clusive_user.can_manage_periods

        self.subjects_string = request.GET.get('subjects')
        if self.subjects_string:
            subject_strings = self.subjects_string.split(',')
            s = Subject.objects.filter(subject__in=subject_strings)
            self.subjects = s

        lengths = request.GET.get('words')
        if lengths:
            self.lengths = lengths.split(',')
        else:
            self.lengths = None

        if self.view == 'period':
            # Make sure period_id is specified and legal.
            if kwargs.get('period_id'):
                self.period = get_object_or_404(Period, id=kwargs.get('period_id'))
                if not self.clusive_user.periods.filter(id=self.period.id).exists():
                    raise Http404('Not a Period of this User.')
            else:
                # Need to set a default period.
                self.period = self.clusive_user.periods.first()
                if not self.period:
                    # No periods, must be a guest user.  Switch to showing public content.
                    return HttpResponseRedirect(redirect_to=reverse('library_style_redirect', kwargs = {'view': 'public'}))
            self.view_name = self.period.name
        else:
            self.view_name = LibraryViews.display_name_of(self.view)
        # Set defaults for next time
        user_changed = False
        # The validity check is a patch for catching the intermittent invalid
        # style view values coming from the kwargs.  See:
        # CSL-1442 https://castudl.atlassian.net/browse/CSL-1442
        if check_valid_choice(LibraryViews.CHOICES, self.view) == False:
            self.view = self.clusive_user.library_view
        if check_valid_choice(LibraryStyles.CHOICES, self.style) == False:
            self.style = self.clusive_user.library_style

        if self.clusive_user.library_view != self.view:
            self.clusive_user.library_view = self.view
            user_changed = True
        if self.period and self.clusive_user.current_period != self.period:
            self.clusive_user.current_period = self.period
            user_changed = True
        if self.clusive_user.library_style != self.style:
            self.clusive_user.library_style = self.style
            user_changed = True
        if user_changed:
            self.clusive_user.save()
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        q: QuerySet
        if self.view == 'period' and self.period:
            q = Book.objects.filter(assignments__period=self.period)
        elif self.view == 'mine':
            q = Book.objects.filter(owner=self.clusive_user)
        elif self.view == 'starred':
            # STARRED = books found in paradata where starred field is true for this user
            q = Book.objects.filter(
                Q(paradata__starred=True)
                & Q(paradata__user=self.clusive_user))
        elif self.view == 'public':
            q = Book.objects.filter(owner=None)
        elif self.view == 'all':
            # ALL = assigned in one of my periods, or public, or owned by me.
            q = Book.objects.filter(
                Q(assignments__period__in=self.clusive_user.periods.all())
                | Q(owner=None)
                | Q(owner=self.clusive_user)).distinct()
        else:
            raise Http404('Unknown view type')

        if self.query:
            q = q.filter(Q(title__icontains=self.query) |
                         Q(author__icontains=self.query) |
                         Q(description__icontains=self.query))

        if self.subjects:
            q  = q.filter(Q(subjects__in=self.subjects))

        if self.lengths:
            length_query = None
            for option in self.lengths:
                if not length_query:
                    length_query = self.query_for_length(option)
                else:
                    length_query |= self.query_for_length(option)
            q = q.filter(length_query)

        if self.sort == 'title':
            q = q.order_by('sort_title', 'sort_author')
        elif self.sort == 'author':
            q = q.order_by('sort_author', 'sort_title')
        else:
            logger.warning('unknown sort setting')

        # Make sure results are not duplicated (can happen with IN queries)
        q = q.distinct()
        # Avoid separate queries for the topic list of every book
        q = q.prefetch_related('subjects')

        # For teachers/parents, also look up relevant BookAssignments and Customizations
        # This queries for just the assignments to Periods that this teacher is in, and attaches it to custom attribute
        if self.clusive_user.can_manage_periods:
            periods = self.clusive_user.periods.all()
            assignment_query = BookAssignment.objects.filter(period__in=periods)
            q = q.prefetch_related(Prefetch('assignments', queryset=assignment_query, to_attr='assign_list'))
            customization_query = Customization.objects.filter(Q(periods__in=periods) | Q(owner=self.clusive_user))
            q = q.prefetch_related(Prefetch('customization_set', queryset=customization_query, to_attr='custom_list'))

        # All of paradata is attached to the book object.
        # Note that in library.py the filter (for starred) is register so that it can be
        # called in the html by the registered name.
        paradata_query = Paradata.objects.filter(user=self.clusive_user)
        q = q.prefetch_related(Prefetch('paradata_set', queryset=paradata_query, to_attr='paradata_list'))

        return q

    def query_for_length(self, size):
        if size=='XS':
            return Q(word_count__lte=500)
        elif size=='S':
            return Q(word_count__gt=500) & Q(word_count__lte=1000)
        elif size=='M':
            return Q(word_count__gt=1000) & Q(word_count__lte=5000)
        elif size=='L':
            return Q(word_count__gt=5000) & Q(word_count__lte=30000)
        if size=='XL':
            return Q(word_count__gt=30000)
        raise Exception('invalid input')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clusive_user'] = self.clusive_user
        context['query'] = self.query
        context['subjects_string'] = self.subjects_string
        context['subjects'] = self.subjects
        context['period'] = self.period
        context['period_name'] = self.period.name if self.period else None
        context['style'] = self.style
        context['current_view'] = self.view
        context['current_view_name'] = self.view_name
        context['sort'] = self.sort
        context['view_names'] = dict(LibraryViews.CHOICES)
        context['topics'] = Subject.get_list()
        context['show_assignments'] = self.show_assignments
        return context


class LibraryView(EventMixin, ThemedPageMixin, SettingsPageMixin, LibraryDataView):
    """
    Full library page showing the controls at the top and the list of cards.
    """
    template_name = 'library/library.html'

    def configure_event(self, event):
        event.page = 'Library'
        event.tip_type = self.tip_shown

    def dispatch(self, request, *args, **kwargs):
        self.search_form = SearchForm(request.GET)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.tip_shown = TipHistory.get_tip_to_show(request.clusive_user, 'Library')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = self.search_form
        context['tip_name'] = self.tip_shown.name if self.tip_shown else None
        context['has_bookshare_account'] = has_bookshare_account(self.request)
        return context


class LibraryStyleRedirectView(View):
    """
    Does a redirect to the user's preferred version of the library page.
    """
    def dispatch(self, request, *args, **kwargs):
        view = kwargs.get('view')
        style = request.clusive_user.library_style
        kwargs = {
            'view': view,
            'sort': 'title',  # FIXME
            'style': style,
        }
        if request.clusive_user and request.clusive_user.current_period:
            kwargs['period_id'] = request.clusive_user.current_period.id
        return HttpResponseRedirect(redirect_to=reverse('library', kwargs=kwargs))


class UploadFormView(LoginRequiredMixin, ThemedPageMixin, SettingsPageMixin, EventMixin, FormView):
    """Parent class for several pages that allow uploading of EPUBs."""
    form_class = UploadForm

    def form_valid(self, form):
        upload = self.request.FILES['file']
        fd, tempfile = mkstemp(suffix=upload.name)
        try:
            with os.fdopen(fd, 'wb') as f:
                for chunk in upload.chunks():
                    f.write(chunk)
            if upload.name.endswith('.docx'):
                (self.bv, changed) = convert_and_unpack_docx_file(self.request.clusive_user, tempfile)
                event_control = 'upload_docx'
            else:
                (self.bv, changed) = unpack_epub_file(self.request.clusive_user, tempfile)
                event_control = 'upload_epub'
            if changed:
                logger.debug('Uploaded file name = %s', upload.name)
                self.bv.filename = upload.name
                self.bv.save()
                logger.debug('Updating word lists')
                scan_book(self.bv.book)
                event = Event.build(session=self.request.session,
                                    type='TOOL_USE_EVENT',
                                    action='USED',
                                    control=event_control,
                                    page=self.page_name, # Defined by subclasses
                                    book_version=self.bv)
                event.save()
            else:
                raise Exception('unpack_epub_file did not find new content.')
            return super().form_valid(form)

        except Exception as e:
            logger.warning('Could not process uploaded file, filename=%s, error=%s',
                           str(upload), e)
            form.add_error('file', 'Could not process uploaded file. Only DOCX and EPUB are allowed.')
            return super().form_invalid(form)

        finally:
            logger.debug("Removing temp file %s" % (tempfile))
            os.remove(tempfile)


class UploadCreateFormView(UploadFormView):
    """Upload an EPUB file as a new Book."""
    template_name = 'library/upload_create.html'
    page_name = 'UploadNew'

    def get_success_url(self):
        return reverse('metadata_upload', kwargs={'pk': self.bv.book.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_bookshare_account'] = has_bookshare_account(self.request)
        context['is_bookshare_connected'] = is_bookshare_connected(self.request)
        return context

    def configure_event(self, event: Event):
        event.page = self.page_name


class UploadReplaceFormView(UploadFormView):
    """Upload an EPUB file to replace an existing Book that you own."""
    template_name = 'library/upload_replace.html'
    page_name = 'UploadReplacement'

    def dispatch(self, request, *args, **kwargs):
        self.orig_book = get_object_or_404(Book, pk=kwargs['pk'])
        if self.orig_book.owner != request.clusive_user:
            return self.handle_no_permission()
        logger.debug('Allowing new upload for owned content: %s', self.orig_book)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orig_book'] = self.orig_book
        return context

    def form_valid(self, form):
        result = super().form_valid(form)
        book = self.bv.book
        book.subjects.set(self.orig_book.subjects.all())
        book.save()
        return result

    def get_success_url(self):
        return reverse('metadata_replace', kwargs={'orig': self.orig_book.pk, 'pk': self.bv.book.pk})

    def configure_event(self, event: Event):
        event.page = self.page_name


class MetadataFormView(LoginRequiredMixin, EventMixin, ThemedPageMixin, SettingsPageMixin, UpdateView):
    """Parent class for several metadata-editing pages."""
    model = Book
    form_class = MetadataForm
    success_url = reverse_lazy('library_style_redirect', kwargs={'view': 'mine'})

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.object.owner != request.clusive_user:
            return self.handle_no_permission()
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orig_filename'] = self.object.versions.first().filename
        return context

    def form_valid(self, form):
        cover = self.request.FILES.get('cover')
        if cover:
            filetype = imghdr.what(cover)
            if not filetype:
                form.add_error('cover', 'Cover must be an image file')
                return super().form_invalid(form)
            else:
                logger.debug('Cover=%s, type is %s', cover, filetype)
                filename = 'cover.' + filetype
                path = self.object.set_cover_file(filename)
                try:
                    with open(path, 'wb') as f:
                        for chunk in cover.chunks():
                            f.write(chunk)
                except Exception as e:
                    logger.error('Could not process uploaded cover image, filename=%s, error=%s',
                               str(cover), str(e))
                    form.add_error('cover', 'Could not process uploaded cover image.')
                    return super().form_invalid(form)

        else:
            logger.debug('Form valid, no cover image')
        messages.success(self.request, 'Reading added. Your readings are indicated by a personal icon ({icon:user-o}) on your library card.')
        return super().form_valid(form)

    def configure_event(self, event: Event):
        event.book_id = self.object.id


class MetadataCreateFormView(MetadataFormView):
    """Edit metadata for a newly-created book. Cancelling will delete it."""
    template_name = 'library/metadata_create.html'

    def configure_event(self, event: Event):
        event.page = 'EditMetadataNew'
        super().configure_event(event)


class MetadataEditFormView(MetadataFormView):
    """Edit metadata for an existing book."""
    template_name = 'library/metadata_edit.html'

    def configure_event(self, event: Event):
        event.page = 'EditMetadata'
        super().configure_event(event)


class MetadataReplaceFormView(MetadataFormView):
    """Edit/choose metadata after uploading a replacement EPUB for an existing book."""
    template_name = 'library/metadata_replace.html'

    def dispatch(self, request, *args, **kwargs):
        self.orig_book = get_object_or_404(Book, pk=kwargs['orig'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orig_book'] = self.orig_book
        return context

    def form_valid(self, form):
        valid = super().form_valid(form)
        # The replacement is confirmed, so orig_book gets updated from the new temp book, which is deleted.
        self.orig_book.title = self.object.title
        self.orig_book.sort_title = self.object.sort_title
        self.orig_book.author = self.object.author
        self.orig_book.sort_author = self.object.sort_author
        self.orig_book.description = self.object.description
        self.orig_book.word_count = self.object.word_count
        self.orig_book.picture_count = self.object.picture_count
        self.orig_book.subjects.set(self.object.subjects.all())

        # Check which cover to use
        if form.cleaned_data['use_orig_cover']:
            logger.debug('Use Orig Cover was requested, making no changes')
        else:
            # Remove old cover, move the new file in place, update DB
            if self.orig_book.cover:
                os.remove(self.orig_book.cover_storage)
                self.orig_book.cover = None
            if self.object.cover:
                path = self.orig_book.set_cover_file(self.object.cover_filename)
                logger.debug('Moving old cover %s to new location %s', self.object.cover_storage, path)
                os.rename(self.object.cover_storage, path)
        self.orig_book.save()

        orig_bv = self.orig_book.versions.get()
        bv = self.object.versions.get()
        orig_bv.word_count = bv.word_count
        orig_bv.picture_count = bv.picture_count
        orig_bv.glossary_words = bv.glossary_words
        orig_bv.all_words = bv.all_words
        orig_bv.new_words = bv.new_words
        orig_bv.non_dict_words = bv.non_dict_words
        orig_bv.mod_date = bv.mod_date
        orig_bv.language = bv.language
        orig_bv.filename = bv.filename
        orig_bv.save()

        shutil.rmtree(orig_bv.storage_dir)
        shutil.move(bv.storage_dir, orig_bv.storage_dir)

        self.object.delete()

        return valid

    def configure_event(self, event: Event):
        event.page = 'EditMetadataReplace'
        super().configure_event(event)


class RemoveBookView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, pk=kwargs['pk'])
        if book.owner != request.clusive_user:
            raise PermissionDenied()
        title = book.title
        book.delete()
        messages.success(request, "Deleted reading \"%s\"" % title)
        event = Event.build(session=self.request.session,
                            type='TOOL_USE_EVENT',
                            action='USED',
                            control='delete_book',
                            page='Library',
                            book_id=kwargs['pk'])
        event.save()
        return redirect('library_style_redirect', view='mine')


class RemoveBookConfirmView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, pk=kwargs['pk'])
        owner = book.owner == request.clusive_user
        context = {'pub': book, 'owner': owner }
        return render(request, 'library/partial/modal_book_delete_confirm.html', context=context)


class ShareDialogView(LoginRequiredMixin, FormView):
    form_class = ShareForm
    template_name = 'library/partial/book_share.html'
    success_url = reverse_lazy('reader_index')
    clusive_user = None
    book = None

    def dispatch(self, request, *args, **kwargs):
        if request.clusive_user.can_manage_periods:
            return super().dispatch(request, *args, **kwargs)
        else:
            self.handle_no_permission()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.clusive_user
        return kwargs

    def get_initial(self):
        return {'periods': self.get_currently_assigned_periods()}

    def get_currently_assigned_periods(self):
        periods = self.clusive_user.periods.all()
        book_assignments = BookAssignment.objects.filter(book=self.book, period__in=periods)
        return [c.period for c in book_assignments]

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.book = get_object_or_404(Book, pk=kwargs['pk'])
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.book = get_object_or_404(Book, pk=kwargs['pk'])
        logger.debug('Posted with user=%s and book=%s', self.clusive_user, self.book)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['book'] = self.book
        return data

    def form_valid(self, form):
        current_assignments = self.get_currently_assigned_periods()
        desired_assignments = form.cleaned_data['periods']
        logger.debug('Submitted: %s', desired_assignments)
        for period in self.clusive_user.periods.all():
            if period in desired_assignments:
                if period not in current_assignments:
                    new_assignment = BookAssignment(book=self.book, period=period)
                    new_assignment.save()
                    logger.debug('Added: %s', new_assignment)
            else:
                if period in current_assignments:
                    old_assignment = BookAssignment.objects.get(book=self.book, period=period)
                    logger.debug('Removed:  %s', old_assignment)
                    old_assignment.delete()
        return super().form_valid(form)

    def form_invalid(self, form):
        # Any combination of periods is reasonable, so there isn't much reason it should come back invalid.
        logger.debug('Submitted form invalid: %s', form.errors)
        return super().form_invalid(form)


class UpdateLastLocationView(LoginRequiredMixin, View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateLastLocationView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        book_id = request.POST.get('book')
        version = request.POST.get('version')
        locator = request.POST.get('locator')
        if not (book_id and version and locator):
            return JsonResponse({
                'status': 'error',
                'error': 'POST must contain book, version, and locator string.'
            }, status=500)
        try:
            Paradata.record_last_location(int(book_id), int(version), clusive_user, locator)
        except Book.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Unknown book.'
            }, status=500)
        else:
            return JsonResponse({'status': 'ok'})


class AnnotationView(LoginRequiredMixin, View):
    """
    POST to this view to add a new annotation to the database.
    DELETE to it to remove one.
    Logically would support the GET method to return information on a highlight or annotation,
    but that is not needed right now.
    """

    def dispatch(self, request, *args, **kwargs):
        return super(AnnotationView, self).dispatch(request, *args, **kwargs)

    # Creates a new annotation or undeletes one
    def post(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        page_event_id = request.POST.get('eventId')
        if request.POST.get('undelete'):
            anno = get_object_or_404(Annotation, id=request.POST.get('undelete'), user=clusive_user)
            anno.dateDeleted = None
            anno.save()
            logger.debug('Undeleting annotation %s', anno)
            annotation_action.send(sender=AnnotationView.__class__,
                                   request=request,
                                   annotation=anno,
                                   event_id=page_event_id,
                                   action='HIGHLIGHTED')
            return JsonResponse({'success': True})
        else:
            book_id = request.POST.get('book')
            version_number = int(request.POST.get('version'))
            highlight = request.POST.get('highlight')
            if not book_id or not highlight:
                raise Http404('POST must contain book, version, and highlight string.')
            try:
                book_version = BookVersion.lookup(book_id, version_number)
                annotation = Annotation(user=clusive_user, bookVersion=book_version, highlight=highlight)
                annotation.update_progression()
                annotation.save()
                # Once a database ID has been generated, we have to update the JSON to include it.
                annotation.update_id()
                annotation.save()
                logger.debug('Created annotation %s', annotation)
                annotation_action.send(sender=AnnotationView.__class__,
                                       request=request,
                                       annotation=annotation,
                                       action='HIGHLIGHTED',
                                       event_id=page_event_id)
            except BookVersion.DoesNotExist:
                raise Http404('Unknown BookVersion: %s / %d' % (book_id, version_number))
            else:
                return JsonResponse({'success': True, 'id': annotation.pk})

    def delete(self, request, *args, **kwargs):
        clusive_user = request.clusive_user
        id = int(kwargs.get('id'))
        anno = get_object_or_404(Annotation, id=id, user=clusive_user)
        logger.debug('Deleting annotation %s', anno)
        anno.dateDeleted = timezone.now()
        anno.save()
        page_event_id = request.GET.get('eventId')
        annotation_action.send(sender=AnnotationView.__class__,
                               request=request,
                               annotation=anno,
                               action='REMOVED',
                               event_id=page_event_id)
        return JsonResponse({'success': True})


class AnnotationListView(LoginRequiredMixin, ListView):
    template_name = 'library/annotation_list.html'
    context_object_name = 'annotations'

    def get_queryset(self):
        clusive_user = get_object_or_404(ClusiveUser, user=self.request.user)
        bookVersion = BookVersion.lookup(self.kwargs['book'], self.kwargs['version'])
        return Annotation.objects.filter(bookVersion=bookVersion, user=clusive_user, dateDeleted=None)


class AnnotationNoteView(LoginRequiredMixin, View):
    """
    For attaching/updating a note belonging to an annotation.
    Only supports POST at the moment. GET is not used since notes are loaded with the page.
    Note: this means if you reload the page with auto-save changes pending, you'll see the outdated content.
    I think this case is rare enough that we can ignore it for now.
    I'd rather not have to do a GET on every single note after page load.
    """
    @staticmethod
    def create_from_request(request, note_data, annotation_id):
        clusive_user = request.clusive_user
        anno = get_object_or_404(Annotation, id=annotation_id, user=clusive_user)
        anno.note = note_data.get('note')
        anno.save()

    def post(self, request, annotation_id):
        try:
            note_data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning('Received malformed note update: %s' % request.body)
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})
        AnnotationNoteView.create_from_request(request, note_data, annotation_id)
        return JsonResponse({"success": "1"})


class SwitchModalContentView(LoginRequiredMixin, TemplateView):
    """Render content of the 'switch' modal with information about versions of a book."""
    template_name = 'shared/partial/modal_switch_content.html'

    def get(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        version = kwargs.get('version')
        book = Book.objects.get(pk=book_id)
        versions = book.versions.all()
        # Count annotations and choose some example words to show
        for v in versions:
            v.annotation_count = Annotation.objects.filter(bookVersion=v, user=request.clusive_user).count()
            if v.sortOrder == 0:
                v.example_words = v.all_word_list[:3]
            else:
                v.example_words = v.new_word_list[:3]
        self.extra_context = {
            'versions': versions,
            'bv': versions[version],
        }
        return super().get(request, *args, **kwargs)


class UpdateTrendsView(View):

    def get(self, request, *args, **kwargs):
        BookTrend.update_all_trends()
        return JsonResponse({'status': 'ok'})


class BookshareConnect(LoginRequiredMixin, TemplateView):
    template_name = 'library/partial/connect_to_bookshare.html'

    def get(self, request, *args, **kwargs):
        if is_bookshare_connected(request):
            request.session['bookshare_connected'] = True
            return HttpResponseRedirect(redirect_to=reverse('my_account'))
        else:
            request.session['bookshare_connected'] = False
            return HttpResponseRedirect(redirect_to='/accounts/bookshare/login/?process=connect&next=/account/my_account')


class BookshareSearch(LoginRequiredMixin, EventMixin, ThemedPageMixin, TemplateView, FormView):
    template_name = 'library/library_search_bookshare.html'
    form_class = BookshareSearchForm
    formlabel ='Step 1: Search by title, author, or ISBN'
    sponsor_warning_message = '\
        You are using a Sponsor (Teacher/District/School) Bookshare account. \
        Your import of Bookshare titles for students is not yet implemented, \
        but coming soon.'

    def dispatch(self, request, *args, **kwargs):
        if not is_bookshare_connected(request):
            # Log into Bookshare and then come back here.
            return HttpResponseRedirect(
                redirect_to='/accounts/bookshare/login?process=connect&next=' + reverse('bookshare_search')
            )
        elif request.clusive_user.can_upload:
            if is_organizational_account(request):
                messages.warning(request, self.sponsor_warning_message)
            self.search_form = BookshareSearchForm(request.POST)
            return super().dispatch(request, *args, **kwargs)
        else:
            self.handle_no_permission()

    def get_success_url(self):
        keyword = self.search_form.clean_keyword()
        # About to start a new Bookshare search.  Clear any existing Bookshare
        # session data
        try:
            del self.request.session['bookshare_search_metadata']
        except:
            pass
        return reverse('bookshare_search_results', kwargs={'keyword': keyword})

    def post(self, request, *args, **kwargs):
        keyword = self.search_form.clean_keyword()
        if keyword == '':
            # endless loop
            return HttpResponseRedirect(redirect_to=reverse('bookshare_search'))
        else:
            return HttpResponseRedirect(redirect_to=self.get_success_url())

    def configure_event(self, event: Event):
        event.page = 'BookshareSearchForm'

class BookshareSearchResults(LoginRequiredMixin, EventMixin, ThemedPageMixin, TemplateView):
    template_name = 'library/library_bookshare_search_results.html'
    query_key = ''
    metadata = {}
    imported_books = []
    search_error = {}
    is_organizational = False

    def dispatch(self, request, *args, **kwargs):
        self.is_organizational = is_organizational_account(request)
        if request.clusive_user.can_upload:
            self.imported_books = self.get_imported_books(request)
            # This view should be called with EITHER a keyword or a page, not both.
            self.query_key = kwargs.get('keyword', '')
            self.page = kwargs.get('page', 1)
            if self.query_key:
                # New search
                logger.debug('New search, keyword = %s', self.query_key)
                self.page = 1
                search_results = self.get_bookshare_metadata(self.request)
                if search_results.get('status_code', 200) == 200:
                    self.metadata = search_results
                    self.search_error = {}
                    request.session['bookshare_search_metadata'] = self.metadata
                else:
                    messages.error(request, search_results['error_message'])
                    self.search_error = search_results
            else:
                if self.is_organizational:
                    messages.warning(request, BookshareSearch.sponsor_warning_message)
                self.metadata = request.session['bookshare_search_metadata']
                pages_available = len(self.metadata['chunks'])
                if self.page <= pages_available:
                    logger.debug('Showing page %d of existing results', self.page)
                    pass
                elif self.page == pages_available+1:
                    logger.debug('Getting next page %d of reults from API', self.page)
                    response = self.extend_bookshare_metadata(self.request, self.metadata)
                    if response.get('status_code', 200) != 200:
                        messages.error(request, response['error_message'])
                        self.search_error = response
                else:
                    # We can only move forward one page at a time.
                    logger.warn('Got request for page %d of search results, only %d available; redirecting to page %d',
                                self.page, pages_available, pages_available+1)
                    return HttpResponseRedirect(redirect_to=reverse('bookshare_search_results',
                                                                    kwargs={ 'page': pages_available+1 }))
            return super().dispatch(request, *args, **kwargs)
        else:
            self.handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chunks = self.metadata.get('chunks', [])
        num_pages = len(chunks)
        # Can we get another page from the API if requested?
        if self.metadata.get('nextLink'):
            num_pages += 1

        # Search errors only occur for the first search or when moving forward
        # to a page of results not yet captured.  Check self.search_error, and
        # if there is an error, set the `current_page` back by one, i.e., one
        # less than the 'next' request had it given no errors.
        if self.search_error.get('status_code', 200) != 200:
            current_page = self.page - 1
        else:
            current_page = self.page

        keyword = self.query_key
        links = {
            'prev': (current_page - 1) if current_page > 1 else None,
            'next': (current_page + 1) if current_page < num_pages else None
        }
        # Create links for pages n-3 to n+3
        first_page_link = max(1, current_page-3)
        last_page_link = min(num_pages, current_page+3)
        page_links = []
        for p in list(range(first_page_link, last_page_link+1)):
            if p == current_page:
                page_links.append('current')
            else:
                page_links.append(p)
        links['pages'] = page_links
        context.update({
            'query_key' : keyword,
            'titles': chunks[current_page-1] if len(chunks) > 0 else [],
            'current_page': current_page,
            'links': links,
            'totalResults': self.metadata.get('totalResults', 'Unknown'),
            'imported_books': self.imported_books,
            'is_organizational': self.is_organizational,
            'member_id': '',
        })
        return context

    def get_bookshare_metadata(self, request):
        if self.query_key == '':
            return {}
        else:
            try:
                access_keys = get_access_keys(request)
                response = self.bookshare_start_search(access_keys)
                if response.get('status_code', 200) != 200:
                    return response
                metadata = {
                    'query': self.query_key,
                    'totalResults': response['totalResults'],
                    'retrieved': len(response['titles']),
                    'nextLink': next((x['href'] for x in response['links'] if x.get('rel', '') == 'next'), None),
                    'chunks': [ response['titles'] ],
                }
                return metadata
            except Exception as e:
                logger.debug("BookshareSearch exception: ", e)
                raise e

    def extend_bookshare_metadata(self, request, metadata):
        """Add one more chunk to the existing search results metadata."""
        access_keys = get_access_keys(request)
        response = self.bookshare_continue_search(access_keys, metadata['nextLink'])
        if response.get('status_code', 200) != 200:
            return response
        metadata['retrieved'] += len(response['titles'])
        metadata['chunks'].append(response['titles'])
        metadata['nextLink'] = next((x['href'] for x in response['links'] if x.get('rel', '') == 'next'), None)
        return metadata

    def bookshare_start_search(self, access_keys):
        """
        Call Bookshare API with a new search term and get first batch of results.
        Successful results of this request should be a JSON structure that
        includes the following:
        totalResults: (integer)
        titles: [ {book}, {book} ]
        links: [ {rel: 'next', href: (URL of next batch of results, if any)} ]
        If the response status is not 200 (success), then the response from
        Bookshare contains a `key` and an array of error `messages`.  See:
        https://apidocs.bookshare.org/reference/index.html#_error_model
        The JSON structure returned in this case is:
        response_status: {integer}
        key: {string} (as returned by Bookshare)
        error_message: {string} (concatenation of messages returned by Bookshare)
        :param access_keys:
        :return:
        """
        access_token = access_keys.get('access_token').token
        href = 'https://api.bookshare.org/v2/titles?' + urlencode({
            'keyword': self.query_key,
            'api_key': access_keys.get('api_key'),
            'formats': 'EPUB3',
            'excludeGlobalCollection': True,
        })
        resp = requests.request(
            'GET',
            href,
            headers={
                'Authorization': 'Bearer ' + access_token
            },
        )
        new_metadata = resp.json()
        logger.debug("Bookshare search response status: %s", resp.status_code)

        # Handle request error, if any.
        if resp.status_code != 200:
           new_metadata['status_code'] = resp.status_code
           self.make_error_message(new_metadata)
           return new_metadata

        return self.filter_metadata(new_metadata)

    def bookshare_continue_search(self, access_keys, url):
        access_token = access_keys.get('access_token').token
        resp = requests.request(
            'GET',
            url,
            headers = {
                'Authorization': 'Bearer ' + access_token
            }
        )
        new_metadata = resp.json()
        logger.debug("Bookshare search response status: %s", resp.status_code)

        # Handle request error, if any.
        if resp.status_code != 200:
            new_metadata['status_code'] = resp.status_code
            self.make_error_message(new_metadata)
            return new_metadata

        return self.filter_metadata(new_metadata)

    def filter_metadata(self, metadata, has_full_access=True):
        """
        Filter the bookshare title search metadata by:
        - whether the user can import it
        - whether the title has an EPUB3 version
        - whether the copyrightDate is None (temporary)
        """
        if metadata['message']:
            logger.warn('Bookshare returned message: %s', metadata['message'])

        for title in metadata.get('titles', []):
            # logger.debug('Found title %s', title.get('title'))
            self.surface_bookshare_info(title, has_full_access)
        return metadata

    def surface_bookshare_info(self, book, has_full_access):
        """
        Add a `clusive` block to the book's Bookshare metadata where the authors
        are taken from Bookshares's `contributors` section, and the thumnbail and
        download urls are taken from the `links` array.  It also creates a shortened
        synopis (200 characters).
        """
        clusive = {}
        for link in book.get('links', []):
            if link['rel'] == 'thumbnail':
                clusive['thumbnail'] = link['href']
            elif link['rel'] == 'self':
                clusive['import_url'] = link['href']

        authors = []
        for contributor in book.get('contributors', []):
            if contributor['type'] == 'author':
                authors.append(contributor['name']['displayName'])
        clusive['authors'] = authors

        if book['synopsis'] is not None:
            clusive['synopsis'] = book['synopsis'][0:200]
            if len(clusive['synopsis']) < len(book['synopsis']):
                clusive['more'] = True
        else:
            clusive['synopsis'] = ''
            clusive['more'] = False

        clusive['epub'] = self.has_epub(book)

        book['clusive'] = clusive

    def has_epub(self, book):
        for aFormat in book.get('formats', []):
            if aFormat['formatId'] == 'EPUB3':
                return True

    def get_imported_books(self, request):
        results = []
        owned_bookhare_books = Book.objects.filter(owner=request.clusive_user, bookshare_id__isnull=False)
        for book in owned_bookhare_books:
            results.append(int(book.bookshare_id))
        return results

    def make_error_message(self, error_response):
        error_messages = ', '.join(error_response['messages'])
        error_response['error_message'] = f"Error: {error_messages}"

    def configure_event(self, event: Event):
        event.page = 'BookshareSearchResults'

class BookshareImport(LoginRequiredMixin, View):
    """
    This API function will return a JSON object with keys:
    * 'status', which is either 'done' (book has been imported), 'pending' (waiting for Bookshare), or 'error'
    * 'message', which has more details on any error.
    * 'id', the ID of the imported book, when done.
    """

    def get(self, request, *args, **kwargs):
        if not request.clusive_user.can_upload:
            raise PermissionDenied('User cannot upload')
        bookshare_id = str(kwargs.get('bookshareId'))
        try:
            access_keys = get_access_keys(request)
        except Exception as e:
            logger.debug("Bookshare Import exception: ", e)
            raise PermissionDenied('No Bookshare access token')

        # Check that it hasn't already been imported.
        # This can happen if the user leaves the site while import is in progress, other other corner cases.
        existing = BookVersion.objects.filter(book__owner=request.clusive_user, book__bookshare_id=bookshare_id)
        if existing:
            logger.debug("Bookshare import exists already: %s", existing)
            return JsonResponse(data={'status': 'done', 'id': existing.first().id})

        # Check if this is an organizational account and, if so, if a user has
        # been provided.  Redirect to choosing an org member is no user was
        # given.
        if is_organizational_account(request):
            for_member = kwargs.get('memberId')
            if for_member == None:
                return HttpResponseRedirect(redirect_to=reverse(
                    'bookshare_org_memberlist',
                    kwargs={'bookshareId': bookshare_id, 'fromSearchPage': 1}
                )
            )
        else:
            for_member = None
        # The following request will return a status code of 202 meaning the
        # request to download has been acknowledged, and a package is being
        # prepared for download.  Subsequent requests will either result in 202
        # again, or, when the package is ready, a 302 redirect to an URL that
        # etrieves the epub content.
        # https://apidocs.bookshare.org/reference/index.html#_responses_3
        the_params = { 'api_key': access_keys.get('api_key') }
        if for_member != None:
            the_params.update({ 'forUser': for_member })
        resp = requests.request(
            'GET',
            'https://api.bookshare.org/v2/titles/' + bookshare_id + '/EPUB3',
            params = the_params,
            headers = {
                'Authorization': 'Bearer ' + access_keys.get('access_token').token
            }
        )
        # 202 - "Download request received; package being prepared"
        if resp.status_code == 202:
            return JsonResponse(data={'status': 'pending', 'message': 'In progress'})
        # 200 - resp contains the epub file
        elif resp.status_code == 200:
            if resp.headers['Content-Type'] == 'application/octet-stream':
                # Also grab the metadata to pass along to import process.
                # TODO: could re-use the metadata that was already fetched as part of the search
                meta_resp = requests.request(
                    'GET',
                    'https://api.bookshare.org/v2/titles/' + bookshare_id,
                    params = { 'api_key': access_keys.get('api_key') },
                    headers = { 'Authorization': 'Bearer ' + access_keys.get('access_token').token }
                )
                metadata = meta_resp.json()
                bv = self.save_book(resp.content, metadata, kwargs)
                return JsonResponse(data={'status': 'done', 'id': bv.book.id})
            else:
                return JsonResponse(data={'status': 'error', 'message': 'Got 200 but not the expected content type.'})
        # If book can't be downloaded, this returns 403
        else:
            bookshare_messages = ', '.join(resp.json().get('messages', []))
            message = f'Error importing the book (code = {resp.status_code}). {bookshare_messages}'
            return JsonResponse(data={'status': 'error', 'message': message})

    def save_book(self, downloaded_contents, bookshare_metadata, kwargs):
        # This is mostly a copy of UploadFormView.form_valid() from above.
        # Consider writing one function to do both.
        bookshare_id = bookshare_metadata['bookshareId']
        fd, tempfile = mkstemp(suffix='epub', prefix=str(bookshare_id))
        # try:
        with os.fdopen(fd, 'wb') as f:
            f.write(downloaded_contents)
        (bv, changed) = unpack_epub_file(self.request.clusive_user, tempfile, bookshare_metadata=bookshare_metadata)
        if changed:
            logger.debug('Uploaded file name = %s', bookshare_id)
            bv.filename = bookshare_id
            bv.save()
            logger.debug('Updating word lists')
            scan_book(bv.book)
            event = Event.build(session=self.request.session,
                                type='TOOL_USE_EVENT',
                                action='USED',
                                control='import_bookshare',
                                page='BookshareSearchResults',
                                book_version=bv)
            event.save()
        else:
            raise Exception('unpack_epub_file did not find new content.')
        return bv

import pdb
class BookshareShowOrgMembers(LoginRequiredMixin, TemplateView):
    template_name = 'library/bookshare_org_members.html'

    def dispatch(self, request, *args, **kwargs):
        logger.debug('BookhareId is: ' + str(kwargs.get('bookshareId')))
        if not is_bookshare_connected(request):
            # Log into Bookshare and then come back here.
            return HttpResponseRedirect(
                redirect_to='/accounts/bookshare/login?process=connect&next=' + reverse('bookshare_org_memberlist')
            )
        else:
            # No book likely means no search results in the session.  Go back
            # to the start of the search to get search results.
            self.book = self.find_book_in_search_results(kwargs['bookshareId'])
            if self.book == None:
                return HttpResponseRedirect(redirect_to=reverse('bookshare_search'))

            bookshare = BookshareOAuth2Adapter(request)
            self.sponsor = bookshare.social_account.uid
            member_accounts = BookshareOrgUserAccount.objects.filter(
                org_user_id = self.sponsor
            )
            self.member_list = []
            for member in member_accounts:
                if member.clusive_user.role != 'ST':
                    continue
                student = {
                    'pk': member.clusive_user.user.id,
                    'name': {
                        'firstName': member.clusive_user.user.first_name,
                        'lastName': member.clusive_user.user.last_name,
                    },
                    'email': member.clusive_user.user.email,
                    'period': member.clusive_user.current_period,
                    'userAccountId': member.account_id
                }
                self.member_list.append(student)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'member_list': self.member_list,
            'book': self.book,
            'search_page': kwargs['fromSearchPage'],
            'sponsor': self.sponsor,
        })
        return context

    def find_book_in_search_results(self, bookshare_id):
        search_metadata = self.request.session.get('bookshare_search_metadata')
        if search_metadata:
            chunks = search_metadata.get('chunks', [])
            book = None
            for chunk in chunks:
                book = next((title for title in chunk if title['bookshareId'] == bookshare_id), None)
                if book:
                    break
            return book
        else:
            return None


class ListCustomizationsView(LoginRequiredMixin, EventMixin, TemplateView):
    template_name = 'library/list_customizations.html'

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, id=kwargs['pk'])
        user =  request.clusive_user
        periods = user.periods.all()
        from_cancel_add = kwargs.get('from_cancel_add', 0) == 1
        # Look up assignments for display, attach as expected by template
        book.assign_list = list(BookAssignment.objects.filter(book=book, period__in=periods))
        # Look up paradata for favorites star
        book.paradata_list = list(Paradata.objects.filter(book=book, user=user))
        # Look up customizations
        customizations = Customization.get_customizations(book, periods, user)
        # If there are no customizations but the user has just cancelled adding
        # one, do not prompt them to add a new one again.  That would be an
        # infinite loop
        if customizations.count() != 0 or from_cancel_add:
            self.extra_context = {
                'book': book,
                'customizations': customizations,
                'period_name': None,
            }
            return super().get(request, *args, **kwargs)
        else:
            # No customizations yet.  Go to the customization editor routing
            # through the add customization handler.
            return HttpResponseRedirect(redirect_to=reverse('customize_add', kwargs={'pk': book.id}))

    def configure_event(self, event: Event):
        event.page = 'ListCustomizations'


class AddCustomizationView(LoginRequiredMixin, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('edit_customization', kwargs={
            'pk': self.customization.id,
            'is_new': 'true',
        })

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, id=kwargs['pk'])
        user = request.clusive_user
        book_customizations = Customization.get_customizations(book, user.periods.all(), user)
        self.customization = Customization(book=book, owner=user)
        self.customization.title = 'Customization ' + str(book_customizations.count()+1)
        self.customization.save()
        self.customization.periods.set(user.periods.all())
        logger.debug('Created customization for book %d: %s', kwargs['pk'], self.customization)
        return super().get(request, *args, **kwargs)


class DeleteCustomizationView(LoginRequiredMixin, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('customize_book', kwargs={
            'pk': kwargs['bk'],
            'from_cancel_add': 1
        })

    def get(self, request, *args, **kwargs):
        try:
            customization = Customization.objects.get(pk=kwargs['ck'])
            logger.debug('Deleting customization for book %d: %s', customization.book.id, customization)
            customization.delete()
        except:
            pass
        return super().get(request, *args, **kwargs)


class EditCustomizationView(LoginRequiredMixin, EventMixin, UpdateView):
    template_name = 'library/edit_customization.html'
    model = Customization
    form_class = EditCustomizationForm

    def dispatch(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.is_new = kwargs.get('is_new', 'false')
        self.request = request
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object.book
        # Look up assignments for display, attach as expected by template
        book.assign_list = list(BookAssignment.objects.filter(book=book, period__in=self.clusive_user.periods.all()))
        # Look up paradata for favorites star
        book.paradata_list = list(Paradata.objects.filter(book=book, user=self.clusive_user))
        context['book'] = book
        context['period_name'] = None
        context['is_new'] = self.is_new
        context['recent_custom_questions'] = self.get_recent_custom_questions(3)
        context['all_words'] = self.object.book.all_word_and_non_dict_word_list
        suggested_words = context['all_words'][:]
        for current_word in self.object.word_list:
            if current_word in suggested_words:
                suggested_words.remove(current_word)
        context['suggested_words'] = suggested_words
        return context

    def get_recent_custom_questions(self, n):
        # Find N most recently-saved questions
        recent = Customization.objects.filter(Q(question__isnull=False)
                                              & ~Q(question='')
                                              & (Q(owner=self.clusive_user)
                                                 | Q(periods__in=self.clusive_user.periods.all()))) \
            .order_by('-updated')
        recent_custom_questions = []
        for c in recent:
            if c.question not in recent_custom_questions:
                recent_custom_questions.append(c.question)
                if len(recent_custom_questions) >= n:
                    break
        return recent_custom_questions

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['clusive_user'] = self.clusive_user
        return kwargs

    def form_valid(self, form):
        result = super().form_valid(form)
        self.modify_custom_vocabulary(form.instance)
        if form.overridden_periods:
            messages.warning(self.request, '%s reassigned to the new customization: %s' %
                             ('Class' if len(form.overridden_periods)==1 else 'Classes',
                              ', '.join([p.name for p in form.overridden_periods])))
        return result

    def get_success_url(self):
        return reverse('customize_book', kwargs={'pk': self.object.book.id})

    def modify_custom_vocabulary(self, customization):
        # Add new words
        new_words_str = self.request.POST.get('new_vocabulary_words', '')
        for new_word in new_words_str.split('|'):
            new_word = new_word.strip()
            # Don't add empty strings
            if len(new_word) > 0:
                custom_vocab_word = CustomVocabularyWord.objects.create(
                    word=new_word, customization=customization
                )
                custom_vocab_word.save()
        # Delete old words marked for deletion
        delete_words_str = self.request.POST.get('delete_vocabulary_words', '')
        for delete_word in delete_words_str.split('|'):
            delete_word = delete_word.strip()
            try:
                # TODO: (JS) Note that get() will fail if the
                # (delete_word,customization) matches more than one record, i.e.
                # multiple instances of a word connected to one customization.
                # Should the CustomVocabularyWord/Customization models restrict
                # the words to be unique?  Vs. support multiple definitions or
                # multiple pronunciations?
                custom_vocab_word = CustomVocabularyWord.objects.get(
                    word=delete_word, customization=customization
                )
                custom_vocab_word.delete()
            except:
                pass

    def configure_event(self, event: Event):
        event.page = 'EditCustomization'
        event.book_id = self.object.book.id


class UpdateStarredRatingView(LoginRequiredMixin, View):
    # starred is the favorite star on the reading and library pages, hidden on dashboard
    # values locallay set sent via url in frontend.js starredButtons function
    # url is /library/setstarred

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateStarredRatingView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not (request.POST.get('book') and request.POST.get('starred')):
            return JsonResponse({
                'status': 'error',
                'error': 'POST must contain book and starred.'
            }, status=500)

        clusive_user_id = request.clusive_user.id
        book_id = int(request.POST.get('book'))
        if request.POST.get('starred').lower() == 'true':
            starred = True
        else:
            starred = False

        try:
            Paradata.record_starred(book_id, clusive_user_id, starred)
        except Book.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Unknown book.'
            }, status=500)

        book_starred.send(self.__class__, request=request, book_id=book_id, starred=starred)
        return JsonResponse({'status': 'ok'})
