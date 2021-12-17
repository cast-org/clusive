from django.urls import path

from . import views

urlpatterns = [
    path('update_trends', views.UpdateTrendsView.as_view(),
         name='update_trends'),
    path('setlocation', views.UpdateLastLocationView.as_view(),
         name='setlocation'),
    path('annotation/<int:id>', views.AnnotationView.as_view(),
         name='annotation_detail'),
    path('annotation', views.AnnotationView.as_view(),
         name='annotation_create'),
    path('annotationlist/<int:book>/<int:version>', views.AnnotationListView.as_view(),
         name='annotation_list'),

    path('annotationnote/<int:annotation_id>', views.AnnotationNoteView.as_view(),
         name='annotation_note'),

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

    path('switch/<int:book_id>/<int:version>', views.SwitchModalContentView.as_view(),
         name='modal_switch'),

    path('bookshare/connect/', views.BookshareConnect.as_view(), name='bookshare_connect'),
    path('bookshare/search/', views.BookshareSearch.as_view(), name='bookshare_search'),
    path('bookshare/search/<keyword>', views.BookshareSearch.as_view(), name='bookshare_search'),
    path('bookshare-results/', views.BookshareSearchResults.as_view(), name='bookshare_search_results'),
    path('bookshare-results/<keyword>', views.BookshareSearchResults.as_view(), name='bookshare_search_results'),
    path('bookshare-results/<keyword>/<int:page>', views.BookshareSearchResults.as_view(), name='bookshare_search_results'),
    path('bookshare-import/<str:bookshareId>/<previous>', views.BookshareImport.as_view(), name='bookshare_import'),
    path('bookshare-import/<str:bookshareId>/<int:previous_page>/<previous>', views.BookshareImport.as_view(), name='bookshare_import'),
    path('bookshare-import/<str:bookshareId>/<int:previous_page>/<previous>/<pending>', views.BookshareImport.as_view(), name='bookshare_import'),

    path('data/<str:style>/<str:sort>/<str:view>/<int:period_id>', views.LibraryDataView.as_view(),
        name='library_data'),
    path('data/<str:style>/<str:sort>/<str:view>/', views.LibraryDataView.as_view(),
         name='library_data'),

    # WARNING: PATTERNS BELOW HERE WILL MATCH ANY URL. PUT MORE SPECIFIC MATCHERS ABOVE.
    path('<str:style>/<str:sort>/<str:view>/<int:period_id>', views.LibraryView.as_view(),
         name='library'),
    path('<str:style>/<str:sort>/<str:view>/', views.LibraryView.as_view(),
         name='library'),

    path('<str:view>', views.LibraryStyleRedirectView.as_view(),
         name='library_style_redirect'),

]
