"""
URL configuration for SnowBeauty project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from snow import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("django-admin/", admin.site.urls),
    # -------------------
    # Public Pages
    # -------------------
    

    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.services, name="services"),
    path("contact/", views.contact, name="contact"),
    path("salon/<int:salon_id>/details/", views.salon_details, name="salon_details"),
    path("search/", views.search_items, name="search_items"),
    path("ajax/filter-services/", views.filter_services_by_type, name="filter_services_by_type"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("book/<int:service_id>/", views.book_service, name="book_service"),
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    # -------------------
    # Owner Pages
    # -------------------
    path("owner/dashboard/", views.owner_dashboard, name="owner_dashboard"),
    path("owner/register-salon/", views.register, name="register_salon"),
    path("owner/edit-profile/", views.edit_profile, name="edit_profile"),
    
   # Owner Products
    path('owner_add_or_edit_product/', views.owner_add_or_edit_product, name='owner_add_or_edit_product'),
    path('owner_add_or_edit_product/<int:pk>/', views.owner_add_or_edit_product, name='owner_edit_product'),
    path('owner_delete_product/<int:pk>/', views.owner_delete_product, name='owner_delete_product'),


    # Owner Services
    path("owner/services/add/", views.owner_add_or_edit_service, name="owner_add_service"),
    path("owner/services/edit/<int:id>/", views.owner_add_or_edit_service, name="owner_edit_service"),
    path("owner/services/delete/<int:id>/", views.owner_delete_service, name="owner_delete_service"),

    # Owner API (Conversations)
    path("api/owner/<int:salon_id>/conversations/", views.api_conversations, name="api_conversations"),
    path("api/conversation/<int:conversation_id>/messages/", views.api_messages, name="api_messages"),
    path("api/conversation/<int:conversation_id>/send/", views.api_send_message, name="api_send_message"),

    # -------------------
    # Admin Pages
    # -------------------
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    
    # Admin Salons
    path("admin/salons/", views.salons_list, name="salons_list"),
    path("admin/salon/approve/<int:salon_id>/", views.approve_salon, name="approve_salon"),
    path("admin/salon/reject/<int:salon_id>/", views.reject_salon, name="reject_salon"),

    # Admin Services
    path("admin/services/", views.services_list, name="services_list"),
    path("admin/services/add/", views.add_service, name="add_service"),
    path("admin/services/edit/<int:pk>/", views.edit_service, name="edit_service"),
    path("admin/services/delete/<int:pk>/", views.delete_service, name="delete_service"),

    # Admin Products
    path("admin/products/", views.products_list, name="products_list"),
    path("admin/products/delete/<int:product_id>/", views.delete_product, name="delete_product"),

    # Admin Users
    path("admin/users/", views.users_list, name="users_list"),
    path("admin/users/edit/<int:id>/", views.edit_user, name="edit_user"),
    path("admin/users/delete/<int:id>/", views.delete_user, name="delete_user"),
    path("admin/users/toggle-status/<int:id>/", views.toggle_user_status, name="toggle_user_status"),
    
    # Admin Approvals
    path("admin/approve-users/", views.admin_approve_users, name="admin_approve_users"),
    path("admin/approve-user/<int:user_id>/", views.approve_user, name="approve_user"),

    # Admin Appointments
    path("admin/appointments/", views.appointments_list, name="appointments_list"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

