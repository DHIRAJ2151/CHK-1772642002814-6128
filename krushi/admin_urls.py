from django.urls import path
from . import admin_views

urlpatterns = [
    path('login/', admin_views.admin_login, name='admin_login'),
    path('', admin_views.dashboard, name='admin_dashboard'),
    path('users/', admin_views.users_list, name='admin_users'),
    path('users/<int:user_id>/toggle/', admin_views.user_toggle_active, name='admin_user_toggle'),
    path('products/', admin_views.products_list, name='admin_products'),
    path('products/new/', admin_views.product_create, name='admin_product_create'),
    path('products/<int:product_id>/edit/', admin_views.product_edit, name='admin_product_edit'),
    path('products/<int:product_id>/delete/', admin_views.product_delete, name='admin_product_delete'),
    path('orders/', admin_views.orders_list, name='admin_orders'),
    path('orders/<int:order_id>/update/', admin_views.order_update_status, name='admin_order_update'),
    path('categories/', admin_views.categories_list, name='admin_categories'),
    path('categories/new/', admin_views.category_create, name='admin_category_create'),
    path('categories/<int:category_id>/delete/', admin_views.category_delete, name='admin_category_delete'),
    path('settings/', admin_views.general_settings, name='admin_settings'),
]
