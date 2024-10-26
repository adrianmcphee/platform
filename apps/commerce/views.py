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
    Cart, CartLineItem, SalesOrder, SalesOrderLineItem, OrganisationWallet, ContributorWallet
)
from apps.product_management.models import Bounty, Product
from apps.security.models import OrganisationPersonRoleAssignment
from apps.security.models import Person
from .forms import AddToCartForm

from .services.payment_service import PaymentService
from .services.cart_service import CartService
from .services.order_service import OrderService
from .services.organisation_wallet_service import OrganisationWalletService
from .services.contributor_wallet_service import ContributorWalletService
from .services.withdrawal_service import PayPalWithdrawalStrategy, USDTWithdrawalStrategy

logger = logging.getLogger(__name__)

@transaction.atomic
@login_required
def bounty_checkout(request):
    try:
        cart = Cart.objects.get(person=request.user.person, status=Cart.CartStatus.OPEN)
    except Cart.DoesNotExist:
        messages.error(request, "No open cart found.")
        return redirect('home')

    try:
        sales_order = SalesOrder.objects.get(cart=cart)
    except SalesOrder.DoesNotExist:
        messages.error(request, "No sales order found for this cart.")
        return redirect('cart')

    if request.method == 'POST':
        success, message = sales_order.process_payment()
        if success:
            messages.success(request, message)
            return redirect('order_confirmation', order_id=sales_order.id)
        else:
            messages.error(request, message)
        return redirect('cart')

    context = {
        'cart': cart,
        'sales_order': sales_order,
    }
    return render(request, 'commerce/checkout.html', context)

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
                cart_service = CartService()
                success, message = cart_service.add_item_to_cart(
                    request.user.person,
                    form.cleaned_data['product'],
                    form.cleaned_data['bounty']
                )
                if success:
                    messages.success(request, message)
                    return redirect('commerce:view_cart')
                else:
                    messages.error(request, message)
            except Exception as e:
                logger.error(f"Error adding item to cart: {str(e)}")
                messages.error(request, "An error occurred while adding the item to the cart.")
        else:
            logger.warning(f"Invalid form data: {form.errors}")
    else:
        form = AddToCartForm()
    
    return render(request, 'add_to_cart.html', {'form': form})

@login_required
def view_cart(request):
    cart_service = CartService()
    cart = cart_service.get_cart(request.user.person)
    return render(request, 'commerce/view_cart.html', {'cart': cart})

@login_required
def checkout(request):
    order_service = OrderService()
    payment_service = PaymentService()
    
    if request.method == 'POST':
        success, order_id, message = order_service.create_order_from_cart(request.user.person)
        if success:
            success, message = payment_service.process_payment(order_id)
            if success:
                messages.success(request, message)
                return redirect('order_confirmation', order_id=order_id)
            else:
                messages.error(request, message)
        else:
            messages.error(request, message)
    
    cart_service = CartService()
    cart = cart_service.get_cart(request.user.person)
    return render(request, 'commerce/checkout.html', {'cart': cart})

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
    contributor_wallet_service = ContributorWalletService()
    wallet, transactions = contributor_wallet_service.get_wallet_info(request.user.person)
    return render(request, 'commerce/view_wallet.html', {'wallet': wallet, 'transactions': transactions})

@login_required
def withdraw_funds(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Logic to process withdrawal
        messages.success(request, f"Withdrawal of ${amount} processed successfully.")
        return redirect('commerce:view_wallet')
    return render(request, 'commerce/withdraw_funds.html')

@login_required
def organisation_wallet_top_up(request):
    org_wallet_service = OrganisationWalletService()
    if request.method == 'POST':
        amount = request.POST.get('amount')
        success, message = org_wallet_service.add_funds(request.user.person, amount)
        if success:
            messages.success(request, message)
            return redirect('commerce:view_organisation_wallet')
        else:
            messages.error(request, message)
    return render(request, 'commerce/organisation_wallet_top_up.html')

@login_required
def view_organisation_wallet(request):
    org_wallet_service = OrganisationWalletService()
    wallet, transactions = org_wallet_service.get_wallet_info(request.user.person)
    return render(request, 'commerce/view_organisation_wallet.html', {'wallet': wallet, 'transactions': transactions})

@login_required
def view_contributor_wallet(request):
    contributor_wallet_service = ContributorWalletService()
    wallet, transactions = contributor_wallet_service.get_wallet_info(request.user.person)
    return render(request, 'commerce/view_contributor_wallet.html', {'wallet': wallet, 'transactions': transactions})

@login_required
def contributor_wallet_withdraw(request):
    contributor_wallet_service = ContributorWalletService()
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        success, message = contributor_wallet_service.process_withdrawal(request.user.person, amount, payment_method)
        if success:
            messages.success(request, message)
            return redirect('commerce:view_contributor_wallet')
        else:
            messages.error(request, message)
    return render(request, 'commerce/contributor_wallet_withdraw.html')

class OrderHistoryView(ListView):
    template_name = 'commerce/order_history.html'
    context_object_name = 'orders'

    def get_queryset(self):
        order_service = OrderService()
        return order_service.get_order_history(self.request.user.person)

class OrderDetailView(DetailView):
    template_name = 'commerce/order_detail.html'
    context_object_name = 'order'

    def get_object(self):
        order_service = OrderService()
        return order_service.get_order_detail(self.request.user.person, self.kwargs['pk'])

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

@login_required
def process_payment(request):
    if request.method == 'POST':
        payment_service = PaymentService()
        amount = request.POST.get('amount')
        method = request.POST.get('method')
        details = {
            # ... payment details from the form ...
        }
        result = payment_service.process_payment(method, amount, details)
        # Handle the result...
    # ...
