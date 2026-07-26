"""
CourseShare Hub — app URL routes.

Routes are added as each slice is built; replace the matching href="#" in
base.html when a route goes live. No app_name namespace (templates use
{% url 'home' %}, not 'hub:home').
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),

    # Auth / profile / contact (§5.1)
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('contact/', views.ContactView.as_view(), name='contact'),

    # Browse (§5.3)
    path('resources/', views.ResourceListView.as_view(), name='resource_list'),
    path('resources/new/', views.ResourceCreateView.as_view(), name='resource_create'),
    path('resources/<int:pk>/', views.ResourceDetailView.as_view(), name='resource_detail'),
    path('resources/<int:pk>/edit/', views.ResourceUpdateView.as_view(), name='resource_update'),
    path('resources/<int:pk>/delete/', views.ResourceDeleteView.as_view(), name='resource_delete'),
    path('resources/<int:pk>/download/', views.resource_download, name='resource_download'),

    # Course / Category browse + management (§5.2, Tianyang)
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/new/', views.CategoryCreateView.as_view(), name='category_create'),
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/new/', views.CourseCreateView.as_view(), name='course_create'),

    # Saved searches (§5.3, Lei)
    path('saved-searches/', views.SavedSearchListView.as_view(), name='saved_searches'),
    path('saved-searches/save/', views.save_search, name='save_search'),
    path('saved-searches/<int:pk>/delete/', views.delete_saved_search, name='delete_saved_search'),

    # Sessions / cookies / history (§5.4)
    path('history/', views.HistoryView.as_view(), name='history'),
    path('history/clear/', views.clear_history, name='clear_history'),

    # Social + static pages (§5.5)
    path('resources/<int:pk>/favourite/', views.toggle_favourite, name='toggle_favourite'),
    path('resources/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('favourites/', views.FavouritesListView.as_view(), name='favourites'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('team/', views.TeamView.as_view(), name='team'),
]
