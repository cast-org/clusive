import imghdr
import json
import logging
import os
import shutil
import requests
import time
from urllib.parse import urlencode
from tempfile import mkstemp

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, FormView, UpdateView, TemplateView

from eventlog.models import Event
from eventlog.signals import annotation_action
from eventlog.views import EventMixin
from library.forms import UploadForm, MetadataForm, ShareForm, SearchForm, BookshareSearchForm, BookshareListResourcesForm
from library.models import Paradata, Book, Annotation, BookVersion, BookAssignment, Subject, BookTrend
from library.parsing import scan_book, convert_and_unpack_docx_file, unpack_epub_file
from pages.views import ThemedPageMixin, SettingsPageMixin
from roster.models import ClusiveUser, Period, LibraryViews, LibraryStyles, check_valid_choice
from tips.models import TipHistory
from oauth2.bookshare.views import has_bookshare_account, is_bookshare_connected, get_access_keys

logger = logging.getLogger(__name__)

import pdb

# The library page requires a lot of parameters, which interact in rather complex ways.
# Here's a summary.  It is a sort-of hierarchy, in that changing parameters higher on this list
# can reset parameters that are lower on the list, but the effects never go in the opposite direction.
#
# STYLE (which should perhaps have been called "layout"): [bricks, grid, list]
#   This is the first part of the URL
#   Changing the style leaves all the other parameters unchanged.
#   The links in the style menu therefore have a JS helper to add the current filter and page to the URL.
#   The ClusiveUser model holds a default for style.
# VIEW (which should perhaps have been called "collection"): [public, mine, or period]
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
        if self.clusive_user.current_period != self.period:
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
        context['style'] = self.style
        context['current_view'] = self.view
        context['current_view_name'] = self.view_name
        context['sort'] = self.sort
        context['view_names'] = dict(LibraryViews.CHOICES)
        context['topics'] = Subject.get_list()
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
            else:
                (self.bv, changed) = unpack_epub_file(self.request.clusive_user, tempfile)
            if changed:
                logger.debug('Uploaded file name = %s', upload.name)
                self.bv.filename = upload.name
                self.bv.save()
                logger.debug('Updating word lists')
                scan_book(self.bv.book)
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

    def get_success_url(self):
        return reverse('metadata_upload', kwargs={'pk': self.bv.book.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_bookshare_account'] = has_bookshare_account(self.request)
        context['is_bookshare_connected'] = is_bookshare_connected(self.request)
        return context

    def configure_event(self, event: Event):
        event.page = 'UploadNew'


class UploadReplaceFormView(UploadFormView):
    """Upload an EPUB file to replace an existing Book that you own."""
    template_name = 'library/upload_replace.html'

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
        event.page = 'UploadReplacement'


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
        return super().form_valid(form)


class MetadataCreateFormView(MetadataFormView):
    """Edit metadata for a newly-created book. Cancelling will delete it."""
    template_name = 'library/metadata_create.html'

    def configure_event(self, event: Event):
        event.page = 'EditMetadataNew'


class MetadataEditFormView(MetadataFormView):
    """Edit metadata for an existing book."""
    template_name = 'library/metadata_edit.html'

    def configure_event(self, event: Event):
        event.page = 'EditMetadata'


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


class RemoveBookView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, pk=kwargs['pk'])
        if book.owner != request.clusive_user:
            raise PermissionDenied()
        book.delete()
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
            return HttpResponseRedirect(redirect_to=reverse('upload'))
        else:
            request.session['bookshare_connected'] = False
            return HttpResponseRedirect(redirect_to='/accounts/bookshare/login?process=connect&next=/library/upload/create')

class BookshareSearch(LoginRequiredMixin, ThemedPageMixin, TemplateView, FormView):  #EventMixin
    template_name = 'library/library_search_bookshare.html'
    form_class = BookshareSearchForm
    formlabel ='Step 1: Search by title, author, or ISBN'

    def dispatch(self, request, *args, **kwargs):
        if not is_bookshare_connected(request):
            # Log into Bookshare and then come back here.
            return HttpResponseRedirect(
                redirect_to='/accounts/bookshare/login?process=connect&next=' + reverse('bookshare_search')
            )
        elif request.clusive_user.can_upload:
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

class BookshareSearchResults(LoginRequiredMixin, ThemedPageMixin, TemplateView):  #EventMixin
    template_name = 'library/library_bookshare_search_results.html'
    query_key = ''
    metadata = {}
    
    def dispatch(self, request, *args, **kwargs):
        if request.clusive_user.can_upload:
            self.query_key = kwargs.get('keyword', '')
            if request.session.get('bookshare_search_metadata') is None:
                self.metadata = self.get_bookshare_metadata(self.request)
                request.session['bookshare_search_metadata'] = self.metadata
            else:
                self.metadata = request.session['bookshare_search_metadata']
            return super().dispatch(request, *args, **kwargs)
        else:
            self.handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # DEBUGGING urls.py
#         keyword = kwargs.get('keyword', '')
#         page = kwargs.get('page', 1)
#         pdb.set_trace()
#         an_url = reverse('bookshare_search_results', kwargs = { 'keyword': keyword, 'page': page })
        # END DEBUGGING

        current_page = kwargs.get('page', 1)
        keyword = kwargs.get('keyword', '')
        bookshare_search_metadata = self.request.session['bookshare_search_metadata']
        chunks = bookshare_search_metadata['chunks']
        chunk_index = current_page - 1;
        links = {
            'prev': None if current_page == 1 else current_page - 1,
            'next': (current_page + 1) if current_page < len(chunks) else None
        }
        pages = [0]*len(chunks)
        pages_index = 0
        while pages_index < len(chunks):
            if pages_index == chunk_index:
                pages[pages_index] = 'current'
            else:
                pages[pages_index] = pages_index + 1
            pages_index += 1
        links['pages'] = pages
        pdb.set_trace()
        context.update({
            'chunks': chunks,
            'chunk_index': chunk_index,
            'current_page': current_page,
            'titles': chunks[chunk_index],                                                    #self.metadata.get('titles', []),
            'links': links,
            'totalResults': bookshare_search_metadata.get('totalResults'),                    #self.metadata.get('totalResults'),
            'clusive_title_count': bookshare_search_metadata.get('clusive_title_count', '?'), #self.metadata.get('clusive_title_count', '?'),
            'duration': bookshare_search_metadata.get('duration', '?'),                       #self.metadata.get('duration', '?'),
            'query_key' : keyword,                                                            #self.query_key,
        })
        return context

    def get_bookshare_metadata(self, request):
        if self.query_key == '':
            return {}
        else:
            try:
                access_keys = get_access_keys(request)
                return self.bookshare_metadata_loop(access_keys)
            except Exception as e:
                logger.debug("BookshareSearch exception: ", e)
                raise e

    def bookshare_metadata_loop(self, access_keys):
        """
        Repeatedly calls Bookshare for the next batch of metadata, filtering
        out titles that the user has no access to.
        """
        common_params = {
            'api_key': access_keys.get('api_key'),
            'formats': 'EPUB3',
            'excludeGlobalCollection': True
        }
        # Check for prefix to do a title or author search vs. keyword search
        is_keyword_search = False
        if self.query_key.startswith('title:'):
            href = 'https://api.bookshare.org/v2/titles?' + urlencode({
                **{'title': self.query_key.replace('title:', '')},
                **common_params
            })
        elif self.query_key.startswith('author:'):
            href = 'https://api.bookshare.org/v2/titles?' + urlencode({
                **{'author': self.query_key.replace('author:', '')},
                **common_params
            })
        else:
            href = 'https://api.bookshare.org/v2/titles?' + urlencode({
                **{'keyword': self.query_key},
                **common_params
            })
            is_keyword_search = True
        logger.debug('Start of Bookshare search using %s', href)
        access_token = access_keys.get('access_token').token
        metadata = {'links': [
            {'rel': 'next', 'href': href}
        ]}
        has_full_access = access_keys.get('proof_status', False)
        new_metadata = None
        collected_metadata = {'chunks': []}

        tic = time.perf_counter()
        while metadata:
            next_link = next((x for x in metadata['links'] if x.get('rel', '') == 'next'), None)
            if next_link:
                resp = requests.request(
                    'GET',
                    next_link['href'],
                    headers = {
                        'Authorization': 'Bearer ' + access_token
                    }
                )
                # Handle 404 or no results
                logger.debug(resp.url)
                new_metadata = resp.json()
                collected_metadata = filter_metadata(new_metadata, collected_metadata, is_keyword_search, has_full_access)
            
            # Processed the next link in the metadata if any.  Continue the
            # filtering with the new meta data, if any.
            metadata = new_metadata
            new_metadata = None

        toc = time.perf_counter()
        duration = f"{toc - tic:0.4f}"
        collected_metadata['duration'] = duration
        logger.debug(f"Bookshare metadata filtering: {toc - tic:0.4f} seconds")
        return collected_metadata

class BookshareImport(LoginRequiredMixin, ThemedPageMixin, TemplateView):  #EventMixin
    template_name = 'library/library_bookshare_import.html'
    bookshare_id = ''
    previous = ''
    title_metadata = {}

    def dispatch(self, request, *args, **kwargs):
        if request.clusive_user.can_upload:
            try:
                access_keys = get_access_keys(request)
            except Exception as e:
                logger.debug("Bookshare Import exception: ", e)
                raise e

            self.bookshare_id = kwargs.get('bookshareId')
            self.previous = kwargs.get('previous')
            resp = requests.request(
                'GET',
                'https://api.bookshare.org/v2/titles/' + self.bookshare_id + '?api_key=' + access_keys.get('api_key'),
                headers = {
                    'Authorization': 'Bearer ' + access_keys.get('access_token').token
                }
            )
            self.title_metadata = resp.json()
            surface_bookshare_info(self.title_metadata, access_keys.get('proof_status', False))
            return super().dispatch(request, *args, **kwargs)
        else:
            self.handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title_metadata,
            'previous': self.previous
        })
        return context

def filter_metadata(metadata, collected_metadata, is_keyword_search, has_full_access=False):
    """
    Filter the bookshare title search metadata by:
    - whether the user can import it
    - whether the title has an EPUB3 version 
    - whether the copyrightDate is None (temporary)
    """
    logger.debug("Metadata filter, message: '%s', next: '%s'", metadata.get('message', 'null'), metadata.get('next', ''))
    if collected_metadata.get('totalResults', 0) == 0:
        collected_metadata['totalResults'] = metadata['totalResults']
        logger.debug("START OF FILTERING, total results = %s", metadata['totalResults'])
        collected_metadata['limit'] = metadata['limit']
        collected_metadata['message'] = metadata['message']
        if collected_metadata.get('titles') is None:
            collected_metadata['titles'] = []

    num_titles_included = 0
    filtered_titles = []
    for title in metadata.get('titles', []):
        copyright = None
        if not has_full_access:
            # Based on Bookshare's advice, the partnerdemo account does not have
            # access to copyrighted titles and only titles with no copyright can
            # be imported
            copyright = title.get('copyright')
            logger.debug("=> COPYRIGHT for %s (%s) is %s", title['title'], title['isbn13'], copyright)
        else:
            copyright = True
            is_available = title.get('available', False)

        if copyright is None or is_available:
            epub_info = check_bookshare_epub_format(title, has_full_access)
            if not (epub_info['epub'] == 'no epub'):
                logger.debug("==> Metadata filter: %s", title['title'])
                surface_bookshare_info(title, has_full_access, epub_info)
                filtered_titles.append(title)
                num_titles_included += 1
                # Not sure what to do about these really.
                collected_metadata['next'] = metadata['next']
                collected_metadata['allows'] = metadata['allows']

    # Append the filtered titles
    collected_metadata['chunks'].append(filtered_titles)
    clusive_title_count = collected_metadata.get('clusive_title_count', 0)
    clusive_title_count += num_titles_included
    collected_metadata['clusive_title_count'] = clusive_title_count
    return collected_metadata

def surface_bookshare_info(book, has_full_access, clusive_addons=None):
    """
    Add a `clusive` block to the book's Bookshare metadata where the authors
    are taken from Bookshares's `contributors` section, and the thumnbail and
    download urls are taken from the `links` array.  It also creates a shortened
    synopis (200 characters).
    """
    clusive = {} if clusive_addons is None else clusive_addons
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
    
    synopsis = ''
    more = False
    if book['synopsis'] is not None:
        synopsis = book['synopsis'][0:200]
        if len(synopsis) < len(book['synopsis']):
            more = True

    if clusive.get('epub') is None:
        clusive.update(check_bookshare_epub_format(book, has_full_access))

    clusive['synopsis'] = synopsis
    clusive['more'] = more
    book['clusive'] = clusive

def check_bookshare_epub_format(book, has_full_access):
    results = {}
    formats = book.get('formats')
    if formats is not None and len(formats) != 0:
        # TODO: use next()?
        results['epub'] = 'no epub'
        for aFormat in formats:
            if aFormat['formatId'] == 'EPUB3':
                results['epub'] = 'has epub'
                break

    # Rationale and assumption of this elif:  if the Bookshare user does not
    # have full access, this function assumes the caller is aware of that, and
    # has determined that the book is in pubilc domain.  Bookshare has advised
    # that publicly available books wiil have an EPUB version but the `formats`
    # metadata will be empty or missing.
    elif has_full_access == False:
        results['epub'] = 'has epub'
    else:
        results['epub'] = 'no formats listed'

    return results
