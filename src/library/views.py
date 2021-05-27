import imghdr
import logging
import os
import shutil
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
from library.forms import UploadForm, MetadataForm, ShareForm, SearchForm
from library.models import Paradata, Book, Annotation, BookVersion, BookAssignment, Subject
from library.parsing import unpack_epub_file, scan_book
from roster.models import ClusiveUser, Period, LibraryViews

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
        if size=='S':
            return Q(word_count__lt=500)
        if size=='M':
            return Q(word_count__gte=500) & Q(word_count__lte=30000)
        if size=='L':
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


class LibraryView(EventMixin, LibraryDataView):
    """
    Full library page showing the controls at the top and the list of cards.
    """
    template_name = 'library/library.html'

    def configure_event(self, event):
        event.page = 'Library'

    def dispatch(self, request, *args, **kwargs):
        self.search_form = SearchForm(request.GET)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = self.search_form
        return context


class LibraryStyleRedirectView(View):
    """
    Does a redirect to the user's preferred version of the library page.
    """
    def dispatch(self, request, *args, **kwargs):
        view = kwargs.get('view')
        style = request.clusive_user.library_style
        return HttpResponseRedirect(redirect_to=reverse('library', kwargs={
            'view': view,
            'sort': 'title',  # FIXME
            'style': style,
        }))


class UploadFormView(LoginRequiredMixin, EventMixin, FormView):
    """Parent class for several pages that allow uploading of EPUBs."""
    form_class = UploadForm

    def form_valid(self, form):
        upload = self.request.FILES['file']
        fd, tempfile = mkstemp()
        try:
            with os.fdopen(fd, 'wb') as f:
                for chunk in upload.chunks():
                    f.write(chunk)
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
            form.add_error('file', 'Could not process uploaded file. Are you sure it is an EPUB file?')
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

    def get_success_url(self):
        return reverse('metadata_replace', kwargs={'orig': self.orig_book.pk, 'pk': self.bv.book.pk})

    def configure_event(self, event: Event):
        event.page = 'UploadReplacement'


class MetadataFormView(LoginRequiredMixin, EventMixin, UpdateView):
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
                path = os.path.join(self.object.storage_dir, filename)
                try:
                    with open(path, 'wb') as f:
                        for chunk in cover.chunks():
                            f.write(chunk)
                except Exception as e:
                    logger.error('Could not process uploaded cover image, filename=%s, error=%s',
                               str(cover), str(e))
                    form.add_error('cover', 'Could not process uploaded cover image.')
                    return super().form_invalid(form)
                self.object.cover = filename

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
        self.orig_book.author = self.object.author
        self.orig_book.description = self.object.description

        # Check which cover to use
        if form.cleaned_data['use_orig_cover']:
            logger.debug('Use Orig Cover was requested, making no changes')
        else:
            # Remove old cover, move the new file in place, update DB
            if self.orig_book.cover:
                os.remove(self.orig_book.cover_storage)
            self.orig_book.cover = self.object.cover
            if self.object.cover:
                os.rename(self.object.cover_storage, self.orig_book.cover_storage)
        self.orig_book.save()

        orig_bv = self.orig_book.versions.get()
        bv = self.object.versions.get()
        orig_bv.glossary_words = bv.glossary_words
        orig_bv.all_words = bv.all_words
        orig_bv.non_dict_words = bv.non_dict_words
        orig_bv.new_words = bv.new_words
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
    POST to this view to add a new highlight to the database.
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
