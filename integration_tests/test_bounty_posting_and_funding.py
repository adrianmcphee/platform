import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.commerce.models import Cart, SalesOrder, OrganisationWallet, Organisation, CartLineItem, OrganisationWalletTransaction
from apps.product_management.models import Bounty, Product, Challenge, Competition
from apps.talent.models import Person
from apps.security.models import User, OrganisationPersonRoleAssignment
import uuid
from apps.common.fields import Base58UUIDv5Field
import base58
from django.conf import settings
import logging
from unittest.mock import patch, PropertyMock, MagicMock

User = get_user_model()

logger = logging.getLogger(__name__)

@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.fixture
def organisation(db, monkeypatch):
    # Mock the PLATFORM_NAMESPACE setting
    monkeypatch.setattr('django.conf.settings.PLATFORM_NAMESPACE', uuid.uuid4())
    
    return Organisation.objects.create(
        name='Test Org',
        country='US'
    )

@pytest.fixture
def wallet(db, organisation):
    return OrganisationWallet.objects.create(organisation=organisation, balance_usd_cents=0)

@pytest.fixture
def bounty(db, product):
    challenge = Challenge.objects.create(
        title="Test Challenge",
        description="This is a test challenge",
        product=product
    )
    return Bounty.objects.create(
        title="Test Bounty",
        description="This is a test bounty",
        product=product,
        challenge=challenge,  # Associate with the challenge
        status=Bounty.BountyStatus.OPEN,
        reward_type='USD',
        reward_in_usd_cents=10000  # $100.00
    )

@pytest.fixture
def bounty_with_points(db):
    return Bounty.objects.create(
        title='Test Bounty with Points',
        reward_in_points=100
    )

@pytest.fixture
def bounty_with_usd(db):
    return Bounty.objects.create(
        title='Test Bounty with USD',
        reward_in_usd_cents=10000  # $100.00
    )

@pytest.fixture
def cart(person, organisation):
    return Cart.objects.create(person=person, organisation=organisation, status=Cart.CartStatus.OPEN)

@pytest.fixture
def person(db):
    user = User.objects.create(username="testuser", email="test@example.com")
    person = Person.objects.create(
        user=user,
        full_name="Test User",
        preferred_name="Test",
        points=0
    )
    return person

@pytest.fixture
def bounty_usd(db):
    return Bounty.objects.create(
        title='Test Bounty USD',
        reward_in_usd_cents=10000  # $100.00
    )

@pytest.fixture
def bounty_points(db):
    return Bounty.objects.create(
        title='Test Bounty Points',
        reward_in_points=100
    )

@pytest.fixture
def product(db):
    return Product.objects.create(name="Test Product")

@pytest.fixture
def bounty_points(db, product):
    return Bounty.objects.create(
        title='Test Bounty Points',
        reward_in_points=100,
        product=product
    )

@pytest.fixture
def bounty_usd(db, product):
    return Bounty.objects.create(
        title='Test Bounty USD',
        reward_in_usd_cents=10000,  # $100.00
        product=product
    )

@pytest.mark.django_db
@patch('apps.commerce.models.OrganisationWallet.deduct_funds')
def test_successful_bounty_checkout_with_sufficient_balance(mock_deduct_funds, client, person, organisation, wallet):
    def side_effect_deduct_funds(wallet, amount_cents, description):
        wallet.balance_usd_cents -= amount_cents
        wallet.save()
        return True

    mock_deduct_funds.side_effect = side_effect_deduct_funds

    # Ensure the person is associated with the user
    user = person.user
    client.force_login(user)

    initial_balance = 20000  # $200.00
    wallet.balance_usd_cents = initial_balance
    wallet.save()

    # Ensure the OrganisationPersonRoleAssignment exists
    OrganisationPersonRoleAssignment.objects.get_or_create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    product = Product.objects.create(
        name="Test Product",
        short_description="A test product",
        full_description="This is a test product for bounty checkout",
        organisation=organisation,
        slug="test-product"
    )

    bounty = Bounty.objects.create(
        title="Test Bounty",
        description="This is a test bounty",
        product=product,
        status=Bounty.BountyStatus.OPEN,
        reward_type='USD',
        reward_in_usd_cents=10000  # $100.00
    )

    # Create cart
    cart = Cart.objects.create(person=person, organisation=organisation)

    # Create bounty line item
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_usd_cents=bounty.reward_in_usd_cents,
        bounty=bounty,
        funding_type=bounty.reward_type
    )

    # Create platform fee line item (assuming 5% fee)
    platform_fee_cents = int(bounty.reward_in_usd_cents * 0.05)
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.PLATFORM_FEE,
        quantity=1,
        unit_price_usd_cents=platform_fee_cents,
        funding_type='USD'
    )

    # Update totals
    cart.update_totals()

    # Get the associated SalesOrder
    sales_order = cart.salesorder

    # Add debug prints
    print(f"Cart status before checkout: {cart.status}")
    print(f"SalesOrder status before checkout: {sales_order.status}")
    print(f"Wallet balance before checkout: {wallet.balance_usd_cents}")

    response = client.post(reverse('commerce:bounty_checkout'))

    print(f"Response content: {response.content.decode()}")
    print(f"Mock deduct_funds called: {mock_deduct_funds.called}")
    print(f"Mock deduct_funds call count: {mock_deduct_funds.call_count}")
    print(f"Mock deduct_funds call args: {mock_deduct_funds.call_args}")

    assert mock_deduct_funds.called, "OrganisationWallet.deduct_funds was not called"
    assert response.status_code == 302
    assert response.url == reverse('commerce:checkout_success')

    cart.refresh_from_db()
    sales_order.refresh_from_db()
    wallet.refresh_from_db()

    print(f"Cart status after checkout: {cart.status}")
    print(f"SalesOrder status after checkout: {sales_order.status}")
    print(f"Wallet balance after checkout: {wallet.balance_usd_cents}")

    assert cart.status == Cart.CartStatus.CHECKED_OUT
    assert sales_order.status == SalesOrder.OrderStatus.COMPLETED

    # Check if a transaction was created
    transaction = OrganisationWalletTransaction.objects.filter(
        wallet=wallet,
        amount_cents=sales_order.total_usd_cents_including_fees_and_taxes,
        transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
        description=f"Payment for order {sales_order.id}"
    ).first()
    assert transaction is not None

    expected_deduction = bounty.reward_in_usd_cents + platform_fee_cents
    print(f"Expected deduction: {expected_deduction}")
    expected_balance = initial_balance - expected_deduction

    # Insert the debug prints here
    print("All transactions:")
    for t in OrganisationWalletTransaction.objects.all():
        print(f"Transaction: wallet={t.wallet}, amount={t.amount_cents}, type={t.transaction_type}, description='{t.description}'")

    transaction_query = OrganisationWalletTransaction.objects.filter(
        wallet=wallet,
        amount_cents=expected_deduction,
        transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
        description=f"Payment for order {sales_order.id}"
    )
    print(f"Transaction query: {transaction_query.query}")
    transaction = transaction_query.first()
    print(f"Found transaction: {transaction}")

    assert cart.status == Cart.CartStatus.CHECKED_OUT
    assert sales_order.status == SalesOrder.OrderStatus.COMPLETED
    assert wallet.balance_usd_cents == expected_balance

    # Check if a transaction was created
    transaction = OrganisationWalletTransaction.objects.filter(
        wallet=wallet,
        amount_cents=expected_deduction,
        transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
        description=f"Payment for order {sales_order.id}"
    ).first()
    assert transaction is not None

@pytest.mark.django_db
@patch('apps.commerce.models.Cart.update_totals')
def test_bounty_checkout_with_wallet_top_up(mock_update_totals, client, person, organisation, wallet, cart):
    cart.total_usd_cents_including_fees_and_taxes = 10000  # $100.00
    cart.save()
    mock_update_totals.return_value = None
    client.force_login(person.user)
    wallet.balance_usd_cents = 5000  # $50.00
    wallet.save()

    product = Product.objects.create(
        name="Test Product",
        short_description="A test product",
        full_description="This is a test product for bounty checkout",
        organisation=organisation,
        slug="test-product"
    )

    bounty = Bounty.objects.create(
        title="Test Bounty",
        description="This is a test bounty",
        product=product,
        status=Bounty.BountyStatus.OPEN,
        reward_type='USD',
        reward_in_usd_cents=10000  # $100.00
    )

    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_usd_cents=10000,
        bounty=bounty,
        funding_type='USD'
    )

    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    response = client.post(reverse('commerce:bounty_checkout'))
    assert response.status_code == 302
    assert response.url == reverse('commerce:checkout_failure')

    # Check that the wallet balance hasn't changed
    wallet.refresh_from_db()
    assert wallet.balance_usd_cents == 5000

    # Check that the cart status hasn't changed
    cart.refresh_from_db()
    assert cart.status == Cart.CartStatus.OPEN

@pytest.mark.django_db
def test_wallet_top_up_failure(client, person, organisation, wallet, cart):
    client.force_login(person.user)
    initial_balance = 5000  # $50.00
    wallet.balance_usd_cents = initial_balance
    wallet.save()

    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    response = client.post(reverse('commerce:wallet_top_up'), {'amount': '-100.00'})
    assert response.status_code == 200
    assert 'Invalid amount' in response.content.decode()

    # Check that the wallet balance hasn't changed
    wallet.refresh_from_db()
    assert wallet.balance_usd_cents == initial_balance

@pytest.mark.django_db
def test_bounty_posting_with_negative_balance(client, person, organisation, wallet, product):
    client.force_login(person.user)
    wallet.balance_usd_cents = -5000  # -$50.00
    wallet.save()

    # Ensure the organisation has a country
    organisation.country = 'US'
    organisation.save()

    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    # Ensure the product is associated with the organisation
    product.organisation = organisation
    product.save()

    bounty = Bounty.objects.create(
        title='Test Bounty',
        description='This is a test bounty',
        product=product,
        status=Bounty.BountyStatus.OPEN,
        reward_type='USD',
        reward_in_usd_cents=10000  # $100.00
    )

    bounty_data = {
        'product': product.id,
        'bounty': bounty.id,
    }

    response = client.post(reverse('commerce:add_to_cart'), bounty_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    
    assert response.status_code == 302, f"Expected redirect, got {response.status_code}"
    assert response.url == reverse('commerce:view_cart'), f"Expected redirect to view_cart, got {response.url}"

    cart = Cart.objects.filter(person=person, organisation=organisation, status=Cart.CartStatus.OPEN).first()
    assert cart is not None, "Cart was not created"
    print(f"Cart: {cart}")
    print(f"Cart organisation: {cart.organisation}")
    assert cart.organisation == organisation, f"Expected organisation {organisation}, got {cart.organisation}"
    assert cart.country == organisation.country, f"Expected country {organisation.country}, got {cart.country}"
    
    # Use the reverse relationship to access cart items
    cart_items = CartLineItem.objects.filter(cart=cart)
    assert cart_items.count() == 1, f"Expected 1 item in cart, got {cart_items.count()}"

    line_item = cart_items.first()
    assert line_item.funding_type == 'USD', f"Expected USD funding type, got {line_item.funding_type}"
    assert line_item.unit_price_usd_cents == 10000, f"Expected 10000 cents, got {line_item.unit_price_usd_cents}"
    assert line_item.unit_price_points is None, f"Expected None for points, got {line_item.unit_price_points}"

@pytest.mark.django_db
def test_mixed_currency_bounty_handling(client, person, organisation, wallet, product):
    client.force_login(person.user)
    wallet.balance_usd_cents = 15000  # $150.00
    wallet.save()

    # Ensure the organisation has a country
    organisation.country = 'US'
    organisation.save()

    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    # Ensure the product is associated with the organisation
    product.organisation = organisation
    product.save()

    usd_bounty = Bounty.objects.create(
        title='USD Bounty',
        description='This bounty has USD reward',
        product=product,
        status=Bounty.BountyStatus.OPEN,
        reward_type='USD',
        reward_in_usd_cents=10000,  # $100.00
    )

    point_bounty = Bounty.objects.create(
        title='Point Bounty',
        description='This bounty has point reward',
        product=product,
        status=Bounty.BountyStatus.OPEN,
        reward_type='POINTS',
        reward_in_points=500
    )

    # Test adding USD bounty
    usd_bounty_data = {
        'product': product.id,
        'bounty': usd_bounty.id,
    }

    response = client.post(reverse('commerce:add_to_cart'), usd_bounty_data)
    assert response.status_code == 302
    assert response.url == reverse('commerce:view_cart')

    # Test adding Point bounty
    point_bounty_data = {
        'product': product.id,
        'bounty': point_bounty.id,
    }

    response = client.post(reverse('commerce:add_to_cart'), point_bounty_data)
    assert response.status_code == 302
    assert response.url == reverse('commerce:view_cart')

    cart = Cart.objects.get(person=person, organisation=organisation, status=Cart.CartStatus.OPEN)
    
    # Use the reverse relationship to access cart items
    cart_items = CartLineItem.objects.filter(cart=cart)
    assert cart_items.count() == 2, f"Expected 2 items in cart, got {cart_items.count()}"

    # Check the details of each cart item
    usd_item = cart_items.filter(funding_type='USD').first()
    point_item = cart_items.filter(funding_type='POINTS').first()

    assert usd_item is not None, "USD item not found in cart"
    assert point_item is not None, "Point item not found in cart"

    assert usd_item.unit_price_usd_cents == 10000, f"Expected 10000 cents for USD item, got {usd_item.unit_price_usd_cents}"
    assert point_item.unit_price_points == 500, f"Expected 500 points for Point item, got {point_item.unit_price_points}"

@pytest.mark.django_db
@patch('apps.commerce.models.Cart.update_totals')
@patch('apps.commerce.models.SalesOrder.process_payment')
def test_bounty_checkout_view_handling(mock_process_payment, mock_update_totals, client, person, organisation, wallet, product):
    def side_effect():
        return True

    mock_process_payment.return_value = True
    mock_update_totals.return_value = None

    client.force_login(person.user)
    cart = Cart.objects.create(person=person, organisation=organisation, status=Cart.CartStatus.OPEN)
    cart.total_usd_cents_including_fees_and_taxes = 10000  # $100.00
    cart.save()

    # Test with insufficient balance
    wallet.balance_usd_cents = 5000  # $50.00
    wallet.save()
    response = client.post(reverse('commerce:bounty_checkout'))
    assert response.status_code == 302
    assert response.url == reverse('commerce:checkout_failure')

    # Test with sufficient balance
    wallet.balance_usd_cents = 15000  # $150.00
    wallet.save()
    response = client.post(reverse('commerce:bounty_checkout'))
    assert response.status_code == 302
    assert response.url == reverse('commerce:checkout_success')

    cart.refresh_from_db()
    assert cart.status == Cart.CartStatus.CHECKED_OUT

    sales_order = SalesOrder.objects.get(cart=cart)
    assert sales_order.status == SalesOrder.OrderStatus.COMPLETED



































