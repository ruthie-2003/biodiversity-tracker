from django.urls import path

from .views import (
    get_species_detail, 
    observation_detail, 
    fetch_and_store_all, 
    homepage_stats, 
    recent_uploads, 
    upgrade_observation_photos,
    get_genus_by_family,
    get_species_by_genus,
    get_family_by_genus,
    get_family_by_species,
    get_genus_by_species,
    get_all_taxa,
    filter_taxa_options,
    filter_observations,
    get_continent,
    search_species_by_name,
    get_continent_options,
    get_species_observations,
    register,
    verify_email,
    login,
    forgot_password,
    reset_password,
    upload_observation,
    user_profile,
    edit_profile,
    dashboard_stats,
    recent_users,
    pending_content,
    export_data,
    search_species_and_users
)

urlpatterns = [
    # Admin
    path('admin/upgrade-photos/', upgrade_observation_photos, name='upgrade_photos'),
    path('admin/stats/', dashboard_stats, name='dashboard_stats'),
    path('admin/recent-users/', recent_users, name='recent_users'),
    path('admin/pending-content/', pending_content, name='pending_content'),
    path('export/<str:format_type>/', export_data, name='export_data'),
    
    path("auth/register/", register, name='register'),
    path("auth/verify-email/", verify_email, name='verify_email'),
    path("auth/login/", login, name='login'),
    path("auth/forgot-password/", forgot_password, name='forgot_password'),
    path("auth/reset-password/", reset_password, name='reset_password'),

    # Data listing
    path('species/<str:species_name>/', get_species_detail, name='get_species_detail'),
    path('species/<str:species_name>/observations/',get_species_observations, name='species_observations'),
    path('observations/<int:source_id>/', observation_detail, name='observation_detail'),
    path('profile/', user_profile, name='user_profile'),
    path('profile/<str:user_id>/', user_profile),
    # exact match comes before dynamic
    path('editprofile/', edit_profile, name='edit_own_profile'),
    path('editprofile/<str:user_id>/', edit_profile, name='edit_profile_by_id'),

    # Fetch & Store
    path('fetch-and-store-all/', fetch_and_store_all, name='fetch_and_store_all'),
    path('upload/', upload_observation, name='upload_observation'),

    # Homepage Stats
    path('homepage/stats/', homepage_stats, name='homepage_stats'),
    path('homepage/uploads/', recent_uploads, name='homepage_uploads'),

    # Taxa APIs
    path('genus-by-family/', get_genus_by_family, name='get_genus_by_family'),
    path('species-by-genus/', get_species_by_genus, name='get_species_by_genus'),
    path('family-by-genus/', get_family_by_genus, name='get_family_by_genus'),
    path('family-by-species/', get_family_by_species, name='get_family_by_species'),
    path('genus-by-species/', get_genus_by_species, name='get_genus_by_species'),
    path('get_all_taxa/', get_all_taxa, name='get_all_taxa'),
    path('filter-options/', filter_taxa_options, name='filter_taxa_options'),
    path('search_species_by_name/', search_species_by_name, name='search_species_by_name'),
    path('search_species_and_users/', search_species_and_users, name='search_species_and_users'),

    # Map + Filters
    path('filter_observations/', filter_observations, name='filter_observations'),
    path('get_continent/', get_continent, name="get_continent"),
    path('get_continent_options/', get_continent_options, name='get_continent_options'),

]
