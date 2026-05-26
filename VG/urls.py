"""
Enhanced URL configuration for VegiGo e-commerce
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from vgapp import views
from vgapp.views import (
    signup_view, login_view, logout_view,
    add_to_cart, view_cart, update_cart, clear_cart,
    checkout, process_checkout, order_success, order_detail,
    profile_view, order_history, get_cart_count,
    CustomPasswordResetView, CustomPasswordResetConfirmView
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # ==================== HOME & PRODUCTS ====================
    path('', views.home, name='home'),
    path('products/', views.product_view, name='products'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # ==================== AUTHENTICATION ====================
    path('auth/signup/', signup_view, name='signup'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    
    # Password Reset
    path('auth/password-reset/', 
         CustomPasswordResetView.as_view(), 
         name='password_reset'),
    path('auth/password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), 
         name='password_reset_done'),
    path('auth/password-reset/confirm/<uidb64>/<token>/', 
         CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('auth/password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # ==================== CART ====================
    path('cart/', view_cart, name='cart'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', update_cart, name='update_cart'),
    path('cart/clear/', clear_cart, name='clear_cart'),
    path('api/cart-count/', get_cart_count, name='get_cart_count'),
    
    # ==================== CHECKOUT & ORDERS ====================
    path('checkout/', checkout, name='checkout'),
    path('checkout/process/', process_checkout, name='process_checkout'),
    path('order/success/<int:order_id>/', order_success, name='order_success'),
    path('order/<int:order_id>/', order_detail, name='order_detail'),
    
    # ==================== USER PROFILE ====================
    path('profile/', profile_view, name='profile'),
    path('orders/', order_history, name='order_history'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
