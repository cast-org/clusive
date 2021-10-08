from django.urls import path

from roster.views import LoginView
from . import views

urlpatterns = [
    path('', LoginView.as_view(), name='index'),
    path('dashboard/<int:period_id>', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard-activity-panel/<int:days>', views.DashboardActivityPanelView.as_view(),
         name='dashboard_activity_panel'),
    path('dashboard-activity-panel-sort/<sort>', views.DashboardActivityPanelView.as_view(),
         name='dashboard_activity_panel_sort'),
    path('reader', views.ReaderIndexView.as_view(), name='reader_index'),
    path('reader/<int:book_id>/<int:version>', views.ReaderView.as_view(), name='reader'),
    path('reader/<int:book_id>', views.ReaderChooseVersionView.as_view(pattern_name='reader'), name='reader_default'),
    path('wordbank', views.WordBankView.as_view(), name='word_bank'),
    path('about', views.AboutView.as_view(), name='about'),
    path('privacy', views.PrivacyView.as_view(), name='privacy'),
    path('debug', views.DebugView.as_view(), name='debug'),
    path('set_star_rating', views.SetStarRatingView.as_view(), name='set_star_rating'),
    path('star_rating_results', views.StarRatingResultsView.as_view(), name='star_rating_results'),
]
