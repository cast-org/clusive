from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from library.models import Paradata, Book, Annotation, BookVersion
from roster.models import ClusiveUser


class UpdateLastLocationView(LoginRequiredMixin,View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateLastLocationView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        book_path = request.POST.get('book')
        locator = request.POST.get('locator')
        if not book_path or not locator:
            raise Http404('POST must contain book and locator string.')
        try:
            Paradata.record_last_location(book_path, clusive_user, locator)
        except Book.DoesNotExist:
            raise Http404('Unknown book path')
        else:
            return JsonResponse({'status': 'ok'})


class AnnotationView(LoginRequiredMixin,View):
    """
    Post to this view to add a new highlight to the database.
    May eventually support the GET method to return information on a highlight or annotation,
    but that is not needed right now.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AnnotationView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        clusive_user = get_object_or_404(ClusiveUser, user=request.user)
        book_path = request.POST.get('book')
        version_number = int(request.POST.get('version'))
        highlight = request.POST.get('highlight')
        if not book_path or not highlight:
            raise Http404('POST must contain book, version, and highlight string.')
        try:
            bookVersion = BookVersion.lookup(book_path, version_number)
            annotation = Annotation(user=clusive_user, bookVersion=bookVersion, highlight=highlight)
            annotation.save()
        except BookVersion.DoesNotExist:
            raise Http404('Unknown BookVersion: %s / %d' % (book_path, version_number))
        else:
            return JsonResponse({'id': annotation.pk})
