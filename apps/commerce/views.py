from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.db import transaction
from django.http import JsonResponse

from .models import (
    Cart, SalesOrder, OrganisationWallet, PayPalPaymentStrategy, USDTPaymentStrategy,
    ContributorWallet, ContributorPayPalWithdrawalStrategy, ContributorUSDTWithdrawalStrategy
)
from apps.product_management.models import Bounty

@login_required
def bounty_checkout(request):
    if request.method == 'POST':
        # Process the checkout
        # ... your checkout logic here ...
        return redirect('checkout_success')  # Redirect to a success page
    else:
        # Display the checkout page
        return render(request, 'commerce/bounty_checkout.html')

@login_required
def wallet_top_up(request, order_id):
    sales_order = get_object_or_404(SalesOrder, id=order_id, cart__person=request.user)
    organisation = request.user.organisation
    wallet = get_object_or_404(OrganisationWallet, organisation=organisation)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount_cents = sales_order.total_usd_cents_including_fees_and_taxes - wallet.balance_usd_cents

        if payment_method == 'paypal':
            strategy = PayPalPaymentStrategy()
            paypal_email = request.POST.get('paypal_email')
            try:
                strategy.validate_payment(paypal_email=paypal_email)
                strategy.process_payment(wallet, amount_cents, paypal_email=paypal_email)
                messages.success(request, "Wallet topped up successfully with PayPal.")
                return redirect('bounty_checkout')
            except ValueError as e:
                messages.error(request, str(e))
        elif payment_method == 'usdt':
            strategy = USDTPaymentStrategy()
            crypto_wallet_address = request.POST.get('crypto_wallet_address')
            try:
                strategy.validate_payment(crypto_wallet_address=crypto_wallet_address)
                strategy.process_payment(wallet, amount_cents, crypto_wallet_address=crypto_wallet_address)
                messages.success(request, "Wallet topped up successfully with USDT.")
                return redirect('bounty_checkout')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Invalid payment method selected.")

    return render(request, 'commerce/wallet_top_up.html', {
        'sales_order': sales_order,
        'wallet': wallet,
        'amount_needed': (sales_order.total_usd_cents_including_fees_and_taxes - wallet.balance_usd_cents) / 100
    })

@login_required
def checkout_success(request):
    return render(request, 'commerce/checkout_success.html')
