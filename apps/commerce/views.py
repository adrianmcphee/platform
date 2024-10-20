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
    Cart, CartLineItem, SalesOrder, SalesOrderLineItem, OrganisationWallet, PayPalPaymentStrategy, USDTPaymentStrategy,
    ContributorWallet, ContributorPayPalWithdrawalStrategy, ContributorUSDTWithdrawalStrategy
)
from apps.product_management.models import Bounty, Product
from apps.security.models import OrganisationPersonRoleAssignment
from apps.security.models import Person
from .forms import AddToCartForm

logger = logging.getLogger(__name__)

@login_required
def bounty_checkout(request):
    print("Entering bounty_checkout view")
    # Get the person associated with the logged-in user
    person = request.user.person
    cart = Cart.objects.filter(person=person, status=Cart.CartStatus.OPEN).first()
    if not cart:
        print("No open cart found")
        return redirect('commerce:checkout_failure')

    sales_order = cart.salesorder
    print(f"SalesOrder ID: {sales_order.id}")
    print(f"SalesOrder total: {sales_order.total_usd_cents_including_fees_and_taxes}")

    wallet = cart.organisation.wallet
    print(f"Wallet balance before: {wallet.balance_usd_cents}")

    if sales_order.process_payment():
        print("Payment processed successfully")
        return redirect('commerce:checkout_success')
    else:
        print("Payment processing failed")
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

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartLineItem, id=item_id, cart__person=request.user.person)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('commerce:view_cart')

@login_required
def update_cart_quantity(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartLineItem, id=item_id, cart__person=request.user.person)
        new_quantity = int(request.POST.get('quantity', 1))
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
            cart_item.cart.update_totals()
            messages.success(request, "Cart updated successfully.")
        else:
            messages.error(request, "Invalid quantity.")
    return redirect('commerce:view_cart')

@login_required
def review_order(request):
    cart = Cart.objects.filter(person=request.user.person, status=Cart.CartStatus.OPEN).first()
    if not cart:
        messages.error(request, "No open cart found.")
        return redirect('commerce:view_cart')
    return render(request, 'commerce/review_order.html', {'cart': cart})

@login_required
def select_payment_method(request):
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        # Logic to set the payment method
        messages.success(request, f"Payment method set to {payment_method}")
        return redirect('commerce:review_order')
    return render(request, 'commerce/select_payment_method.html')

@login_required
def view_wallet(request):
    wallet = OrganisationWallet.objects.filter(organisation__persons=request.user.person).first()
    transactions = wallet.transactions.all()[:10] if wallet else []
    return render(request, 'commerce/view_wallet.html', {'wallet': wallet, 'transactions': transactions})

@login_required
def withdraw_funds(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Logic to process withdrawal
        messages.success(request, f"Withdrawal of ${amount} processed successfully.")
        return redirect('commerce:view_wallet')
    return render(request, 'commerce/withdraw_funds.html')

class OrderHistoryView(ListView):
    model = SalesOrder
    template_name = 'commerce/order_history.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return SalesOrder.objects.filter(person=self.request.user.person)

class OrderDetailView(DetailView):
    model = SalesOrder
    template_name = 'commerce/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return SalesOrder.objects.filter(person=self.request.user.person)

def handle_checkout_error(request, error_message):
    messages.error(request, error_message)
    return redirect('commerce:checkout_failure')

class CartView(ListView):
    model = CartLineItem
    template_name = 'commerce/cart.html'
    context_object_name = 'cart_items'

    def get_queryset(self):
        return CartLineItem.objects.filter(cart__person=self.request.user.person, cart__status=Cart.CartStatus.OPEN)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = Cart.objects.filter(person=self.request.user.person, status=Cart.CartStatus.OPEN).first()
        context['cart'] = cart
        return context
