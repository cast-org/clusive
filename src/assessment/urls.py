from django.urls import path

from . import views

urlpatterns = [
    path('affect_check/<int:book_id>', views.AffectCheckView.as_view(), name='affect_check_view'),
    path('affect_detail/<word>', views.AffectDetailView.as_view(), name='affect_detail_view'),
    path('affect_detail/<word>/<for_user>', views.AffectDetailView.as_view(), name='affect_detail_view'),
    path('comprehension_check/<int:book_id>', views.ComprehensionCheckView.as_view(), name='comprehension_check_view'),
    path('comprehension_detail/<int:book_id>', views.ComprehensionDetailView.as_view(), name='comprehension_detail_view'),
    path('custom_detail/<int:book_id>', views.CustomQuestionDetailView.as_view(), name='custom_detail_view'),
]
