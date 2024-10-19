from django.urls import path
from . import views

urlpatterns = [
    # ... other URL patterns ...
    path('bounty-checkout/', views.bounty_checkout, name='bounty_checkout'),
    path('checkout-success/', views.checkout_success, name='checkout_success'),
    path('wallet-top-up/', views.wallet_top_up, name='wallet_top_up'),
]
