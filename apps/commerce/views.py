from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.db import transaction
from django.http import JsonResponse
import logging

from .models import (
    Cart, SalesOrder, OrganisationWallet, PayPalPaymentStrategy, USDTPaymentStrategy,
    ContributorWallet, ContributorPayPalWithdrawalStrategy, ContributorUSDTWithdrawalStrategy
)
from apps.product_management.models import Bounty
from apps.security.models import OrganisationPersonRoleAssignment

logger = logging.getLogger(__name__)

@login_required
def bounty_checkout(request):
    cart = Cart.objects.get(person=request.user.person, status='Open')
    
    # Get the organisation associated with the person
    org_assignment = OrganisationPersonRoleAssignment.objects.filter(person=request.user.person).first()
    
    if not org_assignment:
        logger.debug("No organisation assignment found")
        return redirect('no_organisation_error')  # Create this view and URL
    
    organisation = org_assignment.organisation
    
    logger.debug(f"Cart total: {cart.total_usd_cents()}, Wallet balance: {organisation.wallet.balance_usd_cents}")
    
    # Check if the wallet has sufficient balance
    if cart.total_usd_cents() <= organisation.wallet.balance_usd_cents:
        logger.debug("Sufficient balance, creating sales order")
        # Create the SalesOrder
        sales_order = SalesOrder.objects.create(
            cart=cart,
            organisation=organisation,
            status='Completed',
            total_usd_cents_excluding_fees_and_taxes=cart.total_usd_cents(),
            total_fees_usd_cents=0,  # You may want to calculate this
            total_taxes_usd_cents=0,  # You may want to calculate this
        )
        
        # Update the cart status
        cart.status = 'Closed'
        cart.save()
        
        # Deduct the amount from the wallet
        wallet = organisation.wallet
        wallet.balance_usd_cents -= cart.total_usd_cents()
        wallet.save()
        
        logger.debug("Redirecting to checkout success")
        return redirect('checkout_success')
    else:
        logger.debug("Insufficient balance, redirecting to wallet top-up")
        return redirect('wallet_top_up')

@login_required
def wallet_top_up(request):
    # For now, we'll just render a simple template
    # You can implement the actual top-up logic later
    return render(request, 'commerce/wallet_top_up.html')

@login_required
def checkout_success(request):
    return render(request, 'commerce/checkout_success.html')
