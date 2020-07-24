from django.urls import path

from . import views

urlpatterns = [
    path('setlocation', views.UpdateLastLocationView.as_view(),
         name='setlocation'),
    path('annotation/<int:id>', views.AnnotationView.as_view(),
         name='annotation_detail'),
    path('annotation', views.AnnotationView.as_view(),
         name='annotation_create'),
    path('annotationlist/<int:book>/<int:version>', views.AnnotationListView.as_view(),
         name='annotation_list'),
    path('upload', views.UploadView.as_view(),
         name='upload'),
    path('metadata/<int:pk>', views.MetadataFormView.as_view(),
         name='metadata'),
    path('<str:view>/<int:period_id>', views.LibraryView.as_view(),
         name='library'),
    path('<str:view>', views.LibraryView.as_view(),
         name='library'),
]
