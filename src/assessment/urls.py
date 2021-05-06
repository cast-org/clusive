from django.urls import path

from . import views

urlpatterns = [    
    path('affect_check/<int:book_id>', views.AffectCheckView.as_view(), name='affect_check_view'),
    path('comprehension_check', views.ComprehensionCheckView.as_view(), name='comprehension_check_set'),    
    path('comprehension_check/<int:book_id>', views.ComprehensionCheckView.as_view(), name='comprehension_check_get')    
]