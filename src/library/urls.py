from django.urls import path

from .views import UpdateLastLocationView, AnnotationView, AnnotationListView, UploadView, MetadataFormView

urlpatterns = [
    path('setlocation', UpdateLastLocationView.as_view(), name='setlocation'),
    path('annotation/<int:id>', AnnotationView.as_view(), name='annotation_detail'),
    path('annotation', AnnotationView.as_view(), name='annotation_create'),
    path('annotationlist/<document>/<int:version>', AnnotationListView.as_view(), name='annotation_list'),
    path('upload', UploadView.as_view(), name='upload'),
    path('metadata', MetadataFormView.as_view(), name='metadata'),
]
