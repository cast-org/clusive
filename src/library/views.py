import imghdr
import logging
import os
from tempfile import mkstemp

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, FormView, UpdateView

from eventlog.signals import annotation_action, page_viewed
from library.forms import UploadForm, MetadataForm, ShareForm
from library.models import Paradata, Book, Annotation, BookVersion, BookAssignment
from library.parsing import unpack_epub_file
from roster.models import ClusiveUser, Period, LibraryViews

logger = logging.getLogger(__name__)


class LibraryView(LoginRequiredMixin, ListView):
    """Library page showing a list of books"""
    template_name = 'library/library.html'
    style = 'grid'
    view = 'public'
    view_name = None  # User-visible name for the current view
    period = None

    def get_queryset(self):
        if self.view == 'period' and self.period:
            return Book.objects.filter(assignments__period=self.period)
        elif self.view == 'mine':
            return Book.objects.filter(owner=self.clusive_user)
        elif self.view == 'public':
            return Book.objects.filter(owner=None)
        elif self.view == 'all':
            # ALL = assigned in one of my periods, or public, or owned by me.
            return Book.objects.filter(
                Q(assignments__period__in=self.clusive_user.periods.all())
                | Q(owner=None)
                | Q(owner=self.clusive_user)).distinct()
        else:
            raise Http404('Unknown view type')

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.view = kwargs.get('view')
        if kwargs.get('style'):
            self.style = kwargs.get('style')
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
                    return HttpResponseRedirect(redirect_to=reverse('library', kwargs = {'view': 'public'}))
            self.view_name = self.period.name
        else:
            self.view_name = LibraryViews.display_name_of(self.view)
        # Set defaults for next time
        self.clusive_user.library_view = self.view
        self.clusive_user.current_period = self.period
        self.clusive_user.save()
        page_viewed.send(self.__class__, request=request, page='library')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clusive_user'] = self.clusive_user
        context['period'] = self.period
        context['style'] = self.style
        context['current_view'] = self.view
        context['current_view_name'] = self.view_name
        context['view_names'] = dict(LibraryViews.CHOICES)
        return context

# class LibraryListView(LibraryView):
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['list_view'] = True
#         return context


class UploadView(LoginRequiredMixin, FormView):
    template_name = 'library/upload.html'
    form_class = UploadForm

    def form_valid(self, form):
        upload = self.request.FILES['file']
        fd, tempfile = mkstemp()
        try:
            with os.fdopen(fd, 'wb') as f:
                for chunk in upload.chunks():
                    f.write(chunk)
            self.bv = unpack_epub_file(self.request.clusive_user, tempfile)
            return super().form_valid(form)

        except Exception as e:
            logger.warning('Could not process uploaded file, filename=%s, error=%s',
                           str(upload), e)
            form.add_error('file', 'Could not process uploaded file. Are you sure it is an EPUB file?')
            return super().form_invalid(form)

        finally:
            logger.debug("Removing temp file %s" % (tempfile))
            os.remove(tempfile)

    def get_success_url(self):
        return reverse('metadata_upload', kwargs={'pk': self.bv.book.pk})


class MetadataFormView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = MetadataForm
    success_url = '/library/mine'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.object.owner != request.clusive_user:
            return self.handle_no_permission()
        return response

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
    template_name = 'library/metadata_create.html'


class MetadataEditFormView(MetadataFormView):
    template_name = 'library/metadata_edit.html'


class RemoveBookView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, pk=kwargs['pk'])
        if book.owner != request.clusive_user:
            raise PermissionDenied()
        book.delete()
        return redirect('library', view='mine')


class RemoveBookConfirmView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, pk=kwargs['pk'])
        owner = book.owner == request.clusive_user
        context = {'pub': book, 'owner': owner }
        return render(request, 'library/partial/modal_book_delete_confirm.html', context=context)


class ShareDialogView(LoginRequiredMixin, FormView):
    form_class = ShareForm
    template_name = 'library/partial/book_share.html'
    success_url = '/'
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
        if request.POST.get('undelete'):
            anno = get_object_or_404(Annotation, id=request.POST.get('undelete'), user=clusive_user)
            anno.dateDeleted = None
            anno.save()
            logger.debug('Undeleting annotation %s', anno)
            annotation_action.send(sender=AnnotationView.__class__,
                                   request=request,
                                   annotation=anno,
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
                                       action='HIGHLIGHTED')
            except BookVersion.DoesNotExist:
                raise Http404('Unknown BookVersion: %s / %d' % (book_id, version_number))
            else:
                return JsonResponse({'success': True, 'id': annotation.pk})

    def delete(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        id = int(kwargs.get('id'))
        anno = get_object_or_404(Annotation, id=id, user=clusive_user)
        logger.debug('Deleting annotation %s', anno)
        anno.dateDeleted = timezone.now()
        anno.save()
        annotation_action.send(sender=AnnotationView.__class__,
                               request=request,
                               annotation=anno,
                               action='REMOVED')
        return JsonResponse({'success': True})


class AnnotationListView(LoginRequiredMixin, ListView):
    template_name = 'library/annotation_list.html'
    context_object_name = 'annotations'

    def get_queryset(self):
        clusive_user = get_object_or_404(ClusiveUser, user=self.request.user)
        bookVersion = BookVersion.lookup(self.kwargs['book'], self.kwargs['version'])
        return Annotation.objects.filter(bookVersion=bookVersion, user=clusive_user, dateDeleted=None)
