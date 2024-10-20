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
    try:
        cart = Cart.objects.get(person=request.user.person, status=Cart.CartStatus.OPEN)
        cart.update_totals()  # This will also update or create the SalesOrder

        sales_order = cart.sales_order
        if sales_order and sales_order.status == SalesOrder.OrderStatus.PENDING:
            # Get the organisation through OrganisationPersonRoleAssignment
            try:
                org_assignment = OrganisationPersonRoleAssignment.objects.get(person=request.user.person, organisation=cart.organisation)
                wallet = org_assignment.organisation.wallet
            except OrganisationPersonRoleAssignment.DoesNotExist:
                messages.error(request, 'You are not associated with the organisation for this cart.')
                return redirect('commerce:checkout_failure')

            # Check if the wallet has sufficient balance
            if wallet.balance_usd_cents < cart.total_usd_cents_including_fees_and_taxes:
                messages.error(request, 'Insufficient balance in the wallet.')
                return redirect('commerce:checkout_failure')

            # Process the payment
            if sales_order.process_payment():
                # Payment successful
                cart.status = Cart.CartStatus.CHECKED_OUT
                cart.save()
                return redirect('commerce:checkout_success')
            else:
                # Payment failed
                messages.error(request, 'Payment processing failed. Please try again.')
                return redirect('commerce:checkout_failure')
        else:
            messages.error(request, 'Invalid cart or sales order status.')
            return redirect('commerce:checkout_failure')
    except Cart.DoesNotExist:
        messages.error(request, 'No active cart found.')
        return redirect('commerce:checkout_failure')
    except Exception as e:
        logger.error(f"Error during checkout: {str(e)}")
        messages.error(request, 'An error occurred during checkout. Please try again.')
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
                    unit_price_usd_cents=bounty.reward_in_usd_cents if bounty.reward_type == 'USD' else 0,
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
    # Add any necessary logic for the checkout failure page
    return render(request, 'commerce/checkout_failure.html')

@login_required
def wallet_success(request):
    return render(request, 'wallet_success.html')
