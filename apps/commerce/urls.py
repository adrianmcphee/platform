from django.urls import path
from . import views

app_name = 'commerce'

urlpatterns = [
    # ... other URL patterns ...
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('view-cart/', views.view_cart, name='view_cart'),
    path('bounty-checkout/', views.bounty_checkout, name='bounty_checkout'),
    path('wallet-top-up/', views.wallet_top_up, name='wallet_top_up'),
    path('checkout-success/', views.checkout_success, name='checkout_success'),
    path('checkout-failure/', views.checkout_failure, name='checkout_failure'),
]
