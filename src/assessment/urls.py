from django.urls import path

from . import views

urlpatterns = [
    path('affect_check/<int:book_id>', views.AffectCheckView.as_view(), name='affect_check_view'),
    path('affect_detail/<word>', views.AffectDetailView.as_view(), name='affect_detail_view'),
    path('comprehension_check/<int:book_id>', views.ComprehensionCheckView.as_view(), name='comprehension_check_view')
]
