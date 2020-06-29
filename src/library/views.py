import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from eventlog.signals import annotation_action
from library.models import Paradata, Book, Annotation, BookVersion
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)


class UpdateLastLocationView(LoginRequiredMixin,View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateLastLocationView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        book_path = request.POST.get('book')
        version = request.POST.get('version')
        locator = request.POST.get('locator')
        if not (book_path and version and locator):
            return JsonResponse({
                'status': 'error',
                'error': 'POST must contain book, version, and locator string.'
            }, status=500)
        try:
            Paradata.record_last_location(book_path, int(version), clusive_user, locator)
        except Book.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Unknown book.'
            }, status=500)
        else:
            return JsonResponse({'status': 'ok'})


class AnnotationView(LoginRequiredMixin,View):
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
                                   annotation = anno,
                                   action='HIGHLIGHTED')
            return JsonResponse({'success': True})
        else:
            book_path = request.POST.get('book')
            version_number = int(request.POST.get('version'))
            highlight = request.POST.get('highlight')
            if not book_path or not highlight:
                raise Http404('POST must contain book, version, and highlight string.')
            try:
                book_version = BookVersion.lookup(book_path, version_number)
                annotation = Annotation(user=clusive_user, bookVersion=book_version, highlight=highlight)
                annotation.update_progression()
                annotation.save()
                # Once a database ID has been generated, we have to update the JSON to include it.
                annotation.update_id()
                annotation.save()
                logger.debug('Created annotation %s', annotation)
                annotation_action.send(sender=AnnotationView.__class__,
                                       request=request,
                                       annotation = annotation,
                                       action='HIGHLIGHTED')
            except BookVersion.DoesNotExist:
                raise Http404('Unknown BookVersion: %s / %d' % (book_path, version_number))
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
                               annotation = anno,
                               action='REMOVED')
        return JsonResponse({'success': True})


class AnnotationListView(LoginRequiredMixin,ListView):
    template_name = 'library/annotation_list.html'
    context_object_name = 'annotations'

    def get_queryset(self):
        clusive_user = get_object_or_404(ClusiveUser, user=self.request.user)
        bookVersion = BookVersion.lookup(self.kwargs['document'], self.kwargs['version'])
        return Annotation.objects.filter(bookVersion=bookVersion, user=clusive_user, dateDeleted=None)
