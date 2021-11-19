import imghdr
import json
import logging
import os
import shutil
import requests
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
from roster.models import ClusiveUser, Period, LibraryViews
from tips.models import TipHistory
from oauth2.bookshare.views import is_bookshare_connected, BookshareOAuth2Adapter

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

import pdb
class BookshareConnect(LoginRequiredMixin, TemplateView):
    template_name = 'library/partial/connect_to_bookshare.html'

    def get(self, request, *args, **kwargs):
#        pdb.set_trace()
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
        return reverse('bookshare_search_results', kwargs={'keyword': keyword})
    
    def post(self, request, *args, **kwargs):
        keyword = self.search_form.clean_keyword()
        if keyword == '':
            # endless loop
            return HttpResponseRedirect(redirect_to=reverse('bookshare_search'))
        else:
            return HttpResponseRedirect(redirect_to=self.get_success_url())

class BookshareSearchResults(LoginRequiredMixin, ThemedPageMixin, TemplateView, FormView):  #EventMixin
    template_name = 'library/library_bookshare_search_results.html'
    form_class = BookshareListResourcesForm
    query_key = ''
    metadata = {}
    
    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        return BookshareListResourcesForm(**kwargs, titles=self.metadata)

    def dispatch(self, request, *args, **kwargs):
        if request.clusive_user.can_upload:
            self.query_key = kwargs.get('keyword', '')
#            self.metadata = {'totalResults': 2183, 'limit': 10, 'message': None, 'titles': [{'allows': None, 'bookshareId': 27601, 'title': 'Frankenstein', 'subtitle': None, 'authors': [{'firstName': 'Mary', 'lastName': 'Shelley', 'middle': 'Wollstonecraft', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': 'En la residencia que el gran poeta Lord Byron tenía en Suiza, vivieron durante algún tiempo la autora  Y su esposo. A Lord Byron se le ocurrió, como pasatiempo, que todos los que vivían en su casa escribieran una historia de horror. La de Mary Godwin fue la de más fortuna,  y, con el título de "Frankenstein o el moderno Prometeo", fue publicada en 1818 con un prólogo de su amante Shelley, posteriormente su marido. En 1831, cuando Mary Godwin, ya viuda de Shelley, publicó la segunda edición de su novela, suprimió algunos pasajes que podrían parecer algo atrevidos. \r\nLa obra tiene un marco literario, histórico y social, que corresponde con lo que podríamos llamar "la bohemia romántica", formada por escritores y artistas más bien iconoclastas con respecto a los valores y costumbres de la época. Es muy posible que Mary Shelley tuviera una vaga intención crítica al mismo tiempo que presentaba, de manera bastante pesimista, una visión utópica costumbres y educación alternativas. Muy importante es considerar que el monstruo es bueno, pero se hace malo al ser injustamente rechazado. Además, había un elemento de fe en el progreso científico que es muy típico de ese tiempo. No olvidemos que el italiano Luigi Galvani había descubierto hacia 1790 lo que se creyó entonces una especie de carga eléctrica animal, que se llamó galvanismo, y que Alessandro Volta, hacia 1800, pudo demostrar con su famosa pila que las descargas eléctricas provocaban contracciones musculares, también en cadáveres.\r\nEsa clase de experimentos, popularizados, causaron una profunda impresión en los públicos de entonces. En la novela de Mary Shelley, la electricidad es necesaria para dar vida al monstruo compuesto de miembros y órganos de cadáveres, y en las películas sobre el tema se utilizan, además de máquinas que no existían en la época de Mary Shelley, las descargas atmosféricas de una noche tormentosa.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2006-12-12T23:10:14Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Mary Wollstonecraft Shelley', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['spa'], 'contentWarnings': [], 'categories': [{'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Short Stories (single author)', 'description': 'FICTION / Short Stories (single author)', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/27601'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/27601/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/3c5/medium/27601.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/3c5/small/27601.jpg'}]}, {'allows': None, 'bookshareId': 1088, 'title': 'Frankenstein, or the Modern Prometheus', 'subtitle': None, 'authors': [{'firstName': 'Mary', 'lastName': 'Shelley', 'middle': 'Wollstonecraft', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': 'Classic horror story. Victor Frankenstein is obsessed with creating life.  His botched creature sets out to destroy Frankenstein, and all he holds dear.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-01-08T05:44:49Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Mary Wollstonecraft Shelley', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Horror', 'description': 'Horror', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Horror', 'description': 'FICTION / Horror', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Literary', 'description': 'FICTION / Literary', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1088'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1088/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/4db/medium/1088.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/4db/small/1088.jpg'}]}, {'allows': None, 'bookshareId': 1602074, 'title': 'Frankenstein, or The Modern Prometheus', 'subtitle': None, 'authors': [{'firstName': 'Mary', 'lastName': 'Shelley', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9781772751666', 'synopsis': 'Frankenstein, or The Modern Prometheus is a novel written by English author Mary Shelley (1797–1851) that tells the story of Victor Frankenstein, a young scientist who creates a grotesque but sapient creature in an unorthodox scientific experiment. His monster has become one of the most recognized characters in all of literature. \r\n', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2018-01-14T08:34:14Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Mary Shelley', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Horror', 'description': 'Horror', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Science Fiction and Fantasy', 'description': 'Science Fiction and Fantasy', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Classics', 'description': 'FICTION / Classics', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / General', 'description': 'FICTION / General', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Gothic', 'description': 'FICTION / Gothic', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1602074'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1602074/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/84c/medium/1602074.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/84c/small/1602074.jpg'}]}, {'allows': None, 'bookshareId': 1602188, 'title': 'Frankenstein, or The Modern Prometheus', 'subtitle': None, 'authors': [{'firstName': 'Mary', 'lastName': 'Shelley', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9781772754308', 'synopsis': 'Frankenstein, or The Modern Prometheus is a novel written by English author Mary Shelley (1797–1851) that tells the story of Victor Frankenstein, a young scientist who creates a grotesque but sapient creature in an unorthodox scientific experiment. His monster has become one of the most recognized characters in all of literature. \r\n', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2018-01-14T08:34:15Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Mary Shelley', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Horror', 'description': 'Horror', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Science Fiction and Fantasy', 'description': 'Science Fiction and Fantasy', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Classics', 'description': 'FICTION / Classics', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / General', 'description': 'FICTION / General', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Gothic', 'description': 'FICTION / Gothic', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1602188'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1602188/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/351/medium/1602188.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/351/small/1602188.jpg'}]}, {'allows': None, 'bookshareId': 2363540, 'title': 'Frankenstein: Or The Modern Prometheus', 'subtitle': 'Or The Modern Prometheus', 'authors': [{'firstName': 'Mary', 'lastName': 'Shelley', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9781945186202', 'synopsis': '"Enduring power.” -The New York TimesPackaged in handsome and affordable trade editions, Clydesdale Classics is a new series of essential literary works. The series features literary phenomena with influence and themes so great that, after their publication, they changed literature forever. From the musings of literary geniuses such as Mark Twain in The Adventures of Huckleberry Finn, to the striking personal narratives from Harriet Jacobs in Incidents in the Life of a Slave Girl, this new series is a comprehensive collection of our literary history through the words of the exceptional few.Frankenstein, or The Modern Prometheus, is often referred to as one the most important literary works of all time. Having been adapted and reprinted thousands of times, and often cited as the birth of the gothic novel and the science fiction genre, Frankenstein has captivated readers for centuries. It is the haunting tale of Victor Frankenstein, a young scientist who creates a grotesque and cognizant being through a scientific experiment. "The monster,” as it’s frequently referred to throughout the novel, consists of sewn body parts from multiple cadavers being used for scientific research. On a dark, stormy night, the creature is brought to life by being shocked with an electrical current harnessed from a lightning storm. The novel explores scientific practices such as galvanism, as well as the ethical repercussions of bringing the deceased back to life.With its grim, but gripping narrative, Frankenstein is the classic story of life and death, humanity and monstrosity, and blurring the lines in between.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': '2018', 'publishDate': '2019-01-09T22:35:54Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Mary Shelley', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'History', 'description': 'History', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Horror', 'description': 'Horror', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Teens', 'description': 'Teens', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Classics', 'description': 'FICTION / Classics', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Gothic', 'description': 'FICTION / Gothic', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Historical', 'description': 'FICTION / Historical', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Horror', 'description': 'FICTION / Horror', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Media Tie-In', 'description': 'FICTION / Media Tie-In', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'YOUNG ADULT FICTION / Horror', 'description': 'YOUNG ADULT FICTION / Horror', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/2363540'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/2363540/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/cbc/medium/2363540.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/cbc/small/2363540.jpg'}]}, {'allows': None, 'bookshareId': 2055167, 'title': 'Frankenstein: Or the Modern Prometheus (Dover Thrift Editions)', 'subtitle': 'Or the Modern Prometheus', 'authors': [{'firstName': 'Mary', 'lastName': 'Shelley', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9780486784755', 'synopsis': 'Few creatures of horror have seized readers\' imaginations and held them for so long as the anguished monster of Mary Shelley\'s Frankenstein. The story of Victor Frankenstein\'s terrible creation and the havoc it caused has enthralled generations of readers and inspired countless writers of horror and suspense. Considering the novel\'s enduring success, it is remarkable that it began merely as a whim of Lord Byron\'s."We will each write a story," Byron announced to his next-door neighbors, Mary Wollstonecraft Godwin and her lover Percy Bysshe Shelley. The friends were summering on the shores of Lake Geneva in Switzerland in 1816, Shelley still unknown as a poet and Byron writing the third canto of Childe Harold. When continued rains kept them confined indoors, all agreed to Byron\'s proposal.The illustrious poets failed to complete their ghost stories, but Mary Shelley rose supremely to the challenge. With Frankenstein, she succeeded admirably in the task she set for herself: to create a story that, in her own words, "would speak to the mysterious fears of our nature and awaken thrilling horror — one to make the reader dread to look round, to curdle the blood, and quicken the beatings of the heart."', 'seriesTitle': 'Dover Thrift Editions', 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2019-05-09T22:53:07Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Mary Shelley', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Horror', 'description': 'Horror', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Science Fiction and Fantasy', 'description': 'Science Fiction and Fantasy', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Classics', 'description': 'FICTION / Classics', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Fantasy / Dark Fantasy', 'description': 'FICTION / Fantasy / Dark Fantasy', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Horror', 'description': 'FICTION / Horror', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': 11, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/2055167'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/2055167/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/d66/medium/2055167.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/d66/small/2055167.jpg'}]}, {'allows': None, 'bookshareId': 1090, 'title': "Frank's Campaign", 'subtitle': None, 'authors': [{'firstName': 'Horatio', 'lastName': 'Alger', 'middle': '', 'prefix': '', 'suffix': 'Jr.', 'links': []}], 'isbn13': None, 'synopsis': None, 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2004-11-05T21:44:18Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Horatio Alger Jr.', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': "Children's Books", 'description': "Children's Books", 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'History', 'description': 'History', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'JUVENILE FICTION / General', 'description': 'JUVENILE FICTION / General', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'JUVENILE FICTION / Historical / United States / Civil War Period (1850-1877)', 'description': 'JUVENILE FICTION / Historical / United States / Civil War Period (1850-1877)', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'JUVENILE FICTION / Lifestyles / Farm & Ranch Life', 'description': 'JUVENILE FICTION / Lifestyles / Farm & Ranch Life', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1090'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1090/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/f61/medium/1090.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/f61/small/1090.jpg'}]}, {'allows': None, 'bookshareId': 434, 'title': 'Ann Veronica', 'subtitle': None, 'authors': [{'firstName': 'H. G.', 'lastName': 'Wells', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': None, 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-01-08T02:17:05Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'H. G. Wells', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Coming of Age', 'description': 'FICTION / Coming of Age', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'FICTION / Literary', 'description': 'FICTION / Literary', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/434'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/434/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/9de/medium/434.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/9de/small/434.jpg'}]}, {'allows': None, 'bookshareId': 1102, 'title': 'On The Firing Line', 'subtitle': None, 'authors': [{'firstName': 'Anna', 'lastName': 'Ray', 'middle': 'Chapin', 'prefix': '', 'suffix': '', 'links': []}, {'firstName': 'Hamilton', 'lastName': 'Fuller', 'middle': 'Brock', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': None, 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-01-08T05:47:54Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Anna Chapin Ray', 'indexName': None, 'links': []}, 'type': 'author'}, {'name': {'displayName': 'Hamilton Brock Fuller', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Romance', 'description': 'Romance', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'FICTION / Romance / General', 'description': 'FICTION / Romance / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1102'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1102/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/2cc/medium/1102.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/2cc/small/1102.jpg'}]}, {'allows': None, 'bookshareId': 1253178, 'title': 'My Father, Frank Lloyd Wright', 'subtitle': None, 'authors': [{'firstName': 'John', 'lastName': 'Wright', 'middle': 'Lloyd', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9780486140629', 'synopsis': '"An anecdotal reminiscence of America\'s chief living genius by his son -- short, unconventional, amusing and on the whole revealing." -- Book Week.Frank Lloyd Wright is widely regarded as the twentieth century\'s greatest architect -- an unconventional genius who transformed both residential and commercial building design with his concept of "organic" architecture. During a long and productive life, Wright designed some 800 buildings, received scores of honors and awards, and left an indelible imprint on modern architectural theory and practice.In this charming, readable memoir, Wright the architect and father comes to life through the vivid recollections and firsthand knowledge of his son. John Lloyd Wright characterizes his father as "a rebel, a jolt to civilization, whose romantic theme -- purposive planning and organic unity in inventing and combining forms -- is an epoch in the architecture of the world." His unique view of the "epoch" will intrigue architects, students, and all who admire the work of this visionary and uncompromising spirit. An added attraction of this volume is the inclusion of the complete text of William C. Gannet\'s The House Beautiful, an extremely rare work designed and printed by Frank Lloyd Wright.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': '1992', 'publishDate': '2018-11-21T18:15:09Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'John Lloyd Wright', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Art and Architecture', 'description': 'Art and Architecture', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Biographies and Memoirs', 'description': 'Biographies and Memoirs', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'ARCHITECTURE / Individual Architects & Firms / General', 'description': 'ARCHITECTURE / Individual Architects & Firms / General', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'BIOGRAPHY & AUTOBIOGRAPHY / Artists, Architects, Photographers', 'description': 'BIOGRAPHY & AUTOBIOGRAPHY / Artists, Architects, Photographers', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1253178'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1253178/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/678/medium/1253178.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/678/small/1253178.jpg'}]}, {'allows': None, 'bookshareId': 1928111, 'title': "Understanding Frank Lloyd Wright's Architecture", 'subtitle': None, 'authors': [{'firstName': 'Donald', 'lastName': 'Hoffmann', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9780486135779', 'synopsis': '"May be the best book on Wright ever written, with the exception of the master\'s own incomparable autobiography." — New York Times Book ReviewDespite the vast literature about Frank Lloyd Wright, noted Wright scholar Donald Hoffmann contends that observations about Wright commonly fail to reach any understanding of his art and few commentaries deal with the principles of his architecture. What inspired his work? How did his architecture mature? What are the dynamics of its characteristic expression? Why will the formative principles always be valid?The answers to these and other questions about Wright\'s architectural philosophy, ideals and methods can be found in this superb treatment, enhanced with 127 photos, plans, and illustrations of a host of Wright masterworks. Among these are the Robie house, the Winslow house, Fallingwater, Hollyhock House, the Larkin Building, Unity Temple, Taliesin, the Guggenheim Museum, the Johnson Wax Building, and many more.Expertly analyzing Wright\'s approach to siting, furnishing, landscaping, and other details, Mr. Hoffmann has written an insightful guide to the concepts that gave Wright\'s architecture "not only its extraordinary vigor of structure and form, expression and meaning, but its surprising continuity." The book will be essential reading for all Wright fans and anyone interested in the evolution of modern architecture.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': '1995', 'publishDate': '2018-11-05T22:31:50Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Donald Hoffmann', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Art and Architecture', 'description': 'Art and Architecture', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'ARCHITECTURE / Individual Architects & Firms / General', 'description': 'ARCHITECTURE / Individual Architects & Firms / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1928111'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1928111/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/1cb/medium/1928111.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/1cb/small/1928111.jpg'}]}, {'allows': None, 'bookshareId': 534, 'title': 'The Autobiography of Benjamin Franklin', 'subtitle': None, 'authors': [{'firstName': 'Benjamin', 'lastName': 'Franklin', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': 'Originally intended as a guide for his son, Benjamin Franklin details his unique and eventful life as an inventor, writer, athlete, scientist, writer and diplomat.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-01-08T02:40:26Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Benjamin Franklin', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Biographies and Memoirs', 'description': 'Biographies and Memoirs', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Politics and Government', 'description': 'Politics and Government', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'POLITICAL SCIENCE / General', 'description': 'POLITICAL SCIENCE / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/534'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/534/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/d30/medium/534.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/d30/small/534.jpg'}]}, {'allows': None, 'bookshareId': 566, 'title': 'Frank Fowler, The Cash Boy', 'subtitle': None, 'authors': [{'firstName': 'Horatio', 'lastName': 'Alger', 'middle': '', 'prefix': '', 'suffix': 'Jr.', 'links': []}], 'isbn13': None, 'synopsis': 'A classic rags to riches story. ', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2004-11-05T21:22:08Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Horatio Alger Jr.', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': "Children's Books", 'description': "Children's Books", 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/566'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/566/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/a9a/medium/566.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/a9a/small/566.jpg'}]}, {'allows': None, 'bookshareId': 1253178, 'title': 'My Father, Frank Lloyd Wright', 'subtitle': None, 'authors': [{'firstName': 'John', 'lastName': 'Wright', 'middle': 'Lloyd', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9780486140629', 'synopsis': '"An anecdotal reminiscence of America\'s chief living genius by his son -- short, unconventional, amusing and on the whole revealing." -- Book Week.Frank Lloyd Wright is widely regarded as the twentieth century\'s greatest architect -- an unconventional genius who transformed both residential and commercial building design with his concept of "organic" architecture. During a long and productive life, Wright designed some 800 buildings, received scores of honors and awards, and left an indelible imprint on modern architectural theory and practice.In this charming, readable memoir, Wright the architect and father comes to life through the vivid recollections and firsthand knowledge of his son. John Lloyd Wright characterizes his father as "a rebel, a jolt to civilization, whose romantic theme -- purposive planning and organic unity in inventing and combining forms -- is an epoch in the architecture of the world." His unique view of the "epoch" will intrigue architects, students, and all who admire the work of this visionary and uncompromising spirit. An added attraction of this volume is the inclusion of the complete text of William C. Gannet\'s The House Beautiful, an extremely rare work designed and printed by Frank Lloyd Wright.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': '1992', 'publishDate': '2018-11-21T18:15:09Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'John Lloyd Wright', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Art and Architecture', 'description': 'Art and Architecture', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Biographies and Memoirs', 'description': 'Biographies and Memoirs', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'ARCHITECTURE / Individual Architects & Firms / General', 'description': 'ARCHITECTURE / Individual Architects & Firms / General', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'BIOGRAPHY & AUTOBIOGRAPHY / Artists, Architects, Photographers', 'description': 'BIOGRAPHY & AUTOBIOGRAPHY / Artists, Architects, Photographers', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1253178'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1253178/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/678/medium/1253178.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/678/small/1253178.jpg'}]}, {'allows': None, 'bookshareId': 1928111, 'title': "Understanding Frank Lloyd Wright's Architecture", 'subtitle': None, 'authors': [{'firstName': 'Donald', 'lastName': 'Hoffmann', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9780486135779', 'synopsis': '"May be the best book on Wright ever written, with the exception of the master\'s own incomparable autobiography." — New York Times Book ReviewDespite the vast literature about Frank Lloyd Wright, noted Wright scholar Donald Hoffmann contends that observations about Wright commonly fail to reach any understanding of his art and few commentaries deal with the principles of his architecture. What inspired his work? How did his architecture mature? What are the dynamics of its characteristic expression? Why will the formative principles always be valid?The answers to these and other questions about Wright\'s architectural philosophy, ideals and methods can be found in this superb treatment, enhanced with 127 photos, plans, and illustrations of a host of Wright masterworks. Among these are the Robie house, the Winslow house, Fallingwater, Hollyhock House, the Larkin Building, Unity Temple, Taliesin, the Guggenheim Museum, the Johnson Wax Building, and many more.Expertly analyzing Wright\'s approach to siting, furnishing, landscaping, and other details, Mr. Hoffmann has written an insightful guide to the concepts that gave Wright\'s architecture "not only its extraordinary vigor of structure and form, expression and meaning, but its surprising continuity." The book will be essential reading for all Wright fans and anyone interested in the evolution of modern architecture.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': '1995', 'publishDate': '2018-11-05T22:31:50Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Donald Hoffmann', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Art and Architecture', 'description': 'Art and Architecture', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'ARCHITECTURE / Individual Architects & Firms / General', 'description': 'ARCHITECTURE / Individual Architects & Firms / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1928111'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1928111/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/1cb/medium/1928111.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/1cb/small/1928111.jpg'}]}, {'allows': None, 'bookshareId': 534, 'title': 'The Autobiography of Benjamin Franklin', 'subtitle': None, 'authors': [{'firstName': 'Benjamin', 'lastName': 'Franklin', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': 'Originally intended as a guide for his son, Benjamin Franklin details his unique and eventful life as an inventor, writer, athlete, scientist, writer and diplomat.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-01-08T02:40:26Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Benjamin Franklin', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Biographies and Memoirs', 'description': 'Biographies and Memoirs', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Politics and Government', 'description': 'Politics and Government', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'POLITICAL SCIENCE / General', 'description': 'POLITICAL SCIENCE / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/534'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/534/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/d30/medium/534.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/d30/small/534.jpg'}]}, {'allows': None, 'bookshareId': 566, 'title': 'Frank Fowler, The Cash Boy', 'subtitle': None, 'authors': [{'firstName': 'Horatio', 'lastName': 'Alger', 'middle': '', 'prefix': '', 'suffix': 'Jr.', 'links': []}], 'isbn13': None, 'synopsis': 'A classic rags to riches story. ', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2004-11-05T21:22:08Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Horatio Alger Jr.', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': "Children's Books", 'description': "Children's Books", 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/566'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/566/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/a9a/medium/566.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/a9a/small/566.jpg'}]}, {'allows': None, 'bookshareId': 1049, 'title': 'Inaugural Speech of Franklin Delano Roosevelt', 'subtitle': None, 'authors': [{'firstName': 'Franklin', 'lastName': 'Roosevelt', 'middle': 'Delano', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': None, 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-01-08T05:33:01Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Franklin Delano Roosevelt', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'History', 'description': 'History', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1049'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1049/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/ede/medium/1049.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/ede/small/1049.jpg'}]}, {'allows': None, 'bookshareId': 1948938, 'title': "Franklin's Way to Wealth and Penn's Maxims", 'subtitle': None, 'authors': [{'firstName': 'Benjamin', 'lastName': 'Franklin', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}, {'firstName': 'William', 'lastName': 'Penn', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': '9780486146522', 'synopsis': 'Witty, wise, and elegant in their simplicity, the timeless adages in this inspiring volume originated with two influential figures of early American history. Franklin’s Way to Wealth began as a preface to Poor Richard’s Almanack, the popular book of advice by Benjamin Franklin, the beloved founding father. Penn’s Maxims features hundreds of observations by the Quaker leader, William Penn,  who founded the colony of Pennsylvania. Both offer enduring counsel on how to live — both materially and spiritually.In addition to his active role in guiding colonial America to independence, Benjamin Franklin was a shrewd businessman who amassed a substantial personal fortune. His life story offers an ideal example of the application of a successful work ethic. In his treatise, he presents his own tried-and-true attitudes toward money management, with quotable thoughts on the rewards of industry, the perils of debt, and the futility of idleness.The democratic principles by which William Penn governed Pennsylvania — including complete freedom of religion, fair trials, and a system of elected representatives — were later adopted into the federal constitution. This collection presents hundreds of his sage reflections, ranging from thoughts on government, education, and religion, to meditations on charity, friendship, and patience.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': '2007', 'publishDate': '2019-01-18T20:31:12Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Benjamin Franklin', 'indexName': None, 'links': []}, 'type': 'author'}, {'name': {'displayName': 'William Penn', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Literature and Fiction', 'description': 'Literature and Fiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'LITERARY COLLECTIONS / American / General', 'description': 'LITERARY COLLECTIONS / American / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/1948938'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/1948938/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/87b/medium/1948938.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/87b/small/1948938.jpg'}]}, {'allows': None, 'bookshareId': 8747, 'title': 'The Letters of Franklin K. Lane', 'subtitle': None, 'authors': [{'firstName': 'Louise', 'lastName': 'Wall', 'middle': 'Herrick', 'prefix': '', 'suffix': '', 'links': []}, {'firstName': 'Anne', 'lastName': 'Wintermute', 'middle': '', 'prefix': '', 'suffix': '', 'links': []}, {'firstName': 'Franklin', 'lastName': 'Lane', 'middle': 'K.', 'prefix': '', 'suffix': '', 'links': []}], 'isbn13': None, 'synopsis': 'A selection of letters written by Franklin K. Lane.', 'seriesTitle': None, 'seriesNumber': None, 'copyrightDate': None, 'publishDate': '2002-05-30T21:47:55Z', 'formats': [{'formatId': 'DAISY', 'name': 'DAISY'}, {'formatId': 'HTML', 'name': 'HTML'}, {'formatId': 'TEXT', 'name': 'Text'}, {'formatId': 'EPUB3', 'name': 'EPUB 3'}, {'formatId': 'DAISY_AUDIO', 'name': 'Audio'}, {'formatId': 'DOCX', 'name': 'Word'}, {'formatId': 'BRF', 'name': 'BRF'}], 'externalFormats': [], 'titleContentType': '', 'available': True, 'contributors': [{'name': {'displayName': 'Louise Herrick Wall', 'indexName': None, 'links': []}, 'type': 'author'}, {'name': {'displayName': 'Anne Wintermute', 'indexName': None, 'links': []}, 'type': 'author'}, {'name': {'displayName': 'Franklin K. Lane', 'indexName': None, 'links': []}, 'type': 'author'}], 'composers': [], 'lyricists': [], 'arrangers': [], 'translators': [], 'editors': None, 'instruments': None, 'vocalParts': None, 'languages': ['eng'], 'contentWarnings': [], 'categories': [{'name': 'Biographies and Memoirs', 'description': 'Biographies and Memoirs', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'History', 'description': 'History', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Military', 'description': 'Military', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Nonfiction', 'description': 'Nonfiction', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'Politics and Government', 'description': 'Politics and Government', 'categoryType': 'Bookshare', 'code': None, 'links': []}, {'name': 'BIOGRAPHY & AUTOBIOGRAPHY / Political', 'description': 'BIOGRAPHY & AUTOBIOGRAPHY / Political', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'HISTORY / Military / World War I', 'description': 'HISTORY / Military / World War I', 'categoryType': 'BISAC', 'code': None, 'links': []}, {'name': 'POLITICAL SCIENCE / American Government / General', 'description': 'POLITICAL SCIENCE / American Government / General', 'categoryType': 'BISAC', 'code': None, 'links': []}], 'readingAgeMinimum': None, 'readingAgeMaximum': None, 'site': 'bookshare', 'links': [{'rel': 'self', 'href': 'https://api.bookshare.org/v2/titles/8747'}, {'rel': 'download', 'href': 'https://api.bookshare.org/v2/titles/8747/{format}'}, {'rel': 'coverimage', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/804/medium/8747.jpg'}, {'rel': 'thumbnail', 'href': 'https://d1lp72kdku3ux1.cloudfront.net/title_instance/804/small/8747.jpg'}]}], 'next': 'AP5xvS_cMPXUANmLrtaNg_dIYqRlntSiSXK2B4XlKULS4SPPknMovRVCHMAw55c3iTYrejBls3Tt7WLLLQl_KAlK_nSs7vhp_w', 'allows': ['POST']}
            self.metadata = self.get_bookshare_metadata(self.request)
            return super().dispatch(request, *args, **kwargs)
        else:
            self.handle_no_permission()

    def get_success_url(self):
        bookshare_id = self.request.POST.get('title_select')
        return reverse('bookshare_search') + bookshare_id
        
    def get_bookshare_metadata(self, request):
        if self.query_key == '':
            return {}
        else:
            bookshare_adapter = BookshareOAuth2Adapter(request)
            try:
                access_keys = bookshare_adapter.get_access_keys()
                return self.bookshare_metadata_loop(access_keys)
            except Exception as e:
                logger.debug("BookshareSearch exception: ", e)
                raise e

    def bookshare_metadata_loop(self, access_keys):
        """
        Repeatedly calls Bookshare for the next batch of metadata, filtering
        out titles that the user has no access to.
        """
        access_token = access_keys.get('access_token').token
        href = 'https://api.bookshare.org/v2/titles?' + urlencode({
            'keyword': self.query_key,
            'api_key': access_keys.get('api_key')
        })
        metadata = {'links': [
            {'rel': 'next', 'href': href}
        ]}
        new_metadata = None
        collected_metadata = {}
                
        while metadata:
            next_link = next((x for x in metadata['links'] if x.get('rel', '') == 'next'), None)
            if next_link:
#                pdb.set_trace()
                resp = requests.request(
                    'GET',
                    next_link['href'],
                    headers = {
                        'Authorization': 'Bearer ' + access_token
                    }
                )
                # Handle 404 or no results
                logger.debug(resp.url)
#                pdb.set_trace()
                new_metadata = resp.json()
                collected_metadata = filter_metadata(new_metadata, collected_metadata)
            
            # Processed the next link in the metadata if any.  Continue the
            # filtering with the new meta data, if any.
            metadata = new_metadata
            new_metadata = None
        
        pdb.set_trace()
        return collected_metadata                   

def filter_metadata(metadata, collected_metadata):
    """
    Filter the bookshare title search metadata by:
    - whether the user can import it
    - whether the title has an EPUB3 version 
    """
    logger.debug("Metadata filter, message: '%s', next: '%s'", metadata.get('message', 'null'), metadata.get('next', ''))
#    pdb.set_trace()
    if collected_metadata.get('totalResults', 0) == 0:
        collected_metadata['totalResults'] = metadata['totalResults']
        collected_metadata['limit'] = metadata['limit']
        collected_metadata['message'] = metadata['message']
        if collected_metadata.get('titles') is None:
            collected_metadata['titles'] = []
    
    new_titles = metadata.get('titles', [])
    for title in new_titles:
        can_import = title.get('available', False)
        # Sometimes metadata inidicates that an EPBUB3 version is available,
        # but sometimes the formats array is null.  For the latter, default to
        # guessing that there is an EPUB3 version.
        if title.get('formats') is None:
            has_epub = True
        else:
            has_epub = next((x for x in title['formats'] if x['formatId'] == 'EPUB3'), None) is not None

        if can_import and has_epub:
            logger.debug("==> Metadata filter: %s", title['title'])
            collected_metadata['titles'].append(title)
            # Not sure what to do about thses really.
            # 'next' about what the next batch of metatadata contains,
            collected_metadata['next'] = metadata['next']
            collected_metadata['allows'] = metadata['allows']
    
    return collected_metadata
