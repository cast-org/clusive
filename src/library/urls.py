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

    path('upload/create', views.UploadCreateFormView.as_view(),
         name='upload'),
    path('upload/replace/<int:pk>', views.UploadReplaceFormView.as_view(),
         name='upload_replace'),
    path('metadata/upload/<int:pk>', views.MetadataCreateFormView.as_view(),
         name='metadata_upload'),
    path('metadata/edit/<int:pk>', views.MetadataEditFormView.as_view(),
         name='metadata_edit'),
    path('metadata/replace/<int:orig>/<int:pk>', views.MetadataReplaceFormView.as_view(),
         name='metadata_replace'),

    path('remove/<int:pk>', views.RemoveBookView.as_view(),
         name='remove'),
    path('remove/confirm/<int:pk>', views.RemoveBookConfirmView.as_view(),
        name='remove_confirm'),

    path('share/<int:pk>', views.ShareDialogView.as_view(),
         name='share'),

    path('<str:style>/<str:view>/<int:period_id>', views.LibraryView.as_view(),
         name='library'),
    path('<str:style>/<str:view>/', views.LibraryView.as_view(),
         name='library'),
    path('<str:view>', views.LibraryView.as_view(),
         name='library'),
]
