from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.db import transaction
from django.http import JsonResponse, HttpResponse
import logging
from unittest.mock import MagicMock

from apps.product_management.forms import BountyForm
from django.views.decorators.http import require_http_methods

from .models import (
    Cart, CartLineItem, SalesOrder, SalesOrderLineItem,OrganisationWallet, PayPalPaymentStrategy, USDTPaymentStrategy,
    ContributorWallet, ContributorPayPalWithdrawalStrategy, ContributorUSDTWithdrawalStrategy
)
from apps.product_management.models import Bounty, Product
from apps.security.models import OrganisationPersonRoleAssignment
from apps.security.models import Person
from .forms import AddToCartForm  # Add this import

logger = logging.getLogger(__name__)

@login_required
def bounty_checkout(request):
    cart = Cart.objects.get(person=request.user.person, status=Cart.CartStatus.OPEN)
    wallet = OrganisationWallet.objects.get(organisation=cart.organisation)
    
    logger.info(f"Starting checkout for cart {cart.id}")
    
    if cart.total_usd_cents_including_fees_and_taxes > wallet.balance_usd_cents:
        logger.warning(f"Insufficient balance for checkout. Cart total: {cart.total_usd_cents_including_fees_and_taxes}, Wallet balance: {wallet.balance_usd_cents}")
        return redirect('commerce:checkout_failure')
    
    sales_order = SalesOrder.objects.create(
        cart=cart,
        organisation=cart.organisation,
        total_usd_cents_excluding_fees_and_taxes=cart.total_usd_cents_excluding_fees_and_taxes,
        total_fees_usd_cents=cart.total_fees_usd_cents,
        total_taxes_usd_cents=cart.total_taxes_usd_cents,
        total_usd_cents_including_fees_and_taxes=cart.total_usd_cents_including_fees_and_taxes,
        status=SalesOrder.OrderStatus.PENDING
    )
    
    if sales_order.process_payment():
        logger.info(f"Payment processed successfully for sales order {sales_order.id}")
        wallet.balance_usd_cents -= cart.total_usd_cents_including_fees_and_taxes
        wallet.save()
        cart.status = Cart.CartStatus.CHECKED_OUT
        cart.save()
        sales_order.status = SalesOrder.OrderStatus.COMPLETED
        sales_order.save()
        return redirect('commerce:checkout_success')
    else:
        logger.error(f"Payment processing failed for sales order {sales_order.id}")
        return redirect('commerce:checkout_failure')

@login_required
def wallet_top_up(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount_cents = int(float(amount) * 100)
            if amount_cents <= 0:
                return HttpResponse("Invalid amount")
            # Implement the logic to top up the wallet
            return HttpResponse("Wallet top-up request received")
        except ValueError:
            return HttpResponse("Invalid amount")
    return HttpResponse("Invalid request method")

@login_required
@require_http_methods(["GET", "POST"])
def add_to_cart(request):
    if request.method == "POST":
        form = AddToCartForm(request.POST)
        if form.is_valid():
            try:
                product = form.cleaned_data['product']
                bounty = form.cleaned_data['bounty']
                
                # Get the organisation from the product
                organisation = product.organisation
                if not organisation:
                    raise ValueError("Product does not have an associated organisation")
                
                cart, created = Cart.objects.get_or_create(
                    person=request.user.person,
                    organisation=organisation,
                    status=Cart.CartStatus.OPEN,
                    defaults={'country': organisation.country}
                )
                
                CartLineItem.objects.create(
                    cart=cart,
                    item_type=CartLineItem.ItemType.BOUNTY,
                    quantity=1,
                    unit_price_usd_cents=bounty.reward_in_usd_cents if bounty.reward_type == 'USD' else None,
                    unit_price_points=bounty.reward_in_points if bounty.reward_type == 'POINTS' else None,
                    bounty=bounty,
                    funding_type=bounty.reward_type
                )
                
                cart.update_totals()
                logger.info(f"Item added to cart {cart.id} successfully")
                return redirect('commerce:view_cart')
            except Exception as e:
                logger.error(f"Error adding item to cart: {str(e)}")
                form.add_error(None, "An error occurred while adding the item to the cart.")
        else:
            logger.warning(f"Invalid form data: {form.errors}")
    else:
        form = AddToCartForm()
    
    return render(request, 'add_to_cart.html', {'form': form})

@login_required
def view_cart(request):
    # Implement the logic to view the cart
    return render(request, 'commerce/view_cart.html')

@login_required
def checkout_success(request):
    return render(request, 'checkout_success.html')

@login_required
def checkout_failure(request):
    return render(request, 'checkout_failure.html')

@login_required
def wallet_success(request):
    return render(request, 'wallet_success.html')
