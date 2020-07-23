import logging
import os
import sys
from tempfile import mkstemp

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, TemplateView, FormView

from eventlog.signals import annotation_action, page_viewed
from library.forms import UploadForm
from library.models import Paradata, Book, Annotation, BookVersion, BookAssignment
from library.parsing import unpack_epub_file
from roster.models import ClusiveUser, Period, LibraryViews

logger = logging.getLogger(__name__)


class LibraryView(LoginRequiredMixin, ListView):
    """Library page showing a list of books"""
    template_name = 'library/library.html'
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
                | Q(owner=self.clusive_user))
        else:
            raise Http404('Unknown view type')

    def get(self, request, *args, **kwargs):
        self.clusive_user = request.clusive_user
        self.view = kwargs.get('view')
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
        context['current_view'] = self.view
        context['current_view_name'] = self.view_name
        context['view_names'] = dict(LibraryViews.CHOICES)
        return context


class UploadView(LoginRequiredMixin, FormView):
    template_name = 'library/upload.html'
    form_class = UploadForm
    success_url = '/library/metadata'

    def form_valid(self, form):
        upload = self.request.FILES['file']
        fd, tempfile = mkstemp()
        try:
            with os.fdopen(fd, 'wb') as f:
                for chunk in upload.chunks():
                    f.write(chunk)
            self.bv = unpack_epub_file(self.request.clusive_user, tempfile)
            return super().form_valid(form)

        except:
            e = sys.exc_info()[0]
            logger.warning('Could not process uploaded file, filename=%s, error=%s',
                           str(upload), e)
            form.add_error('file', 'Could not process uploaded file. Are you sure it is an EPUB file?')
            return super().form_invalid(form)

        finally:
            logger.debug("Removing temp file %s" % (tempfile))
            os.remove(tempfile)

    def get_success_url(self):
        return self.success_url + '?bv=%d' % (self.bv.pk)


class MetadataFormView(LoginRequiredMixin, TemplateView):
    template_name = 'library/metadata.html'

    def get(self, request, *args, **kwargs):
        bv_id = request.GET.get('bv')
        bv = get_object_or_404(BookVersion, pk=bv_id)
        cover = bv.path + '/' + bv.book.cover if bv.book.cover else None
        self.extra_context = {'title': bv.book.title, 'cover_src': cover}
        return super().get(request, *args, **kwargs)


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
