import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.commerce.models import Cart, SalesOrder, OrganisationWallet, Organisation, CartLineItem
from apps.product_management.models import Bounty, Product, Challenge, Competition
from apps.talent.models import Person
from apps.security.models import User, OrganisationPersonRoleAssignment
import uuid
from apps.common.fields import Base58UUIDv5Field
import base58
from django.conf import settings
import logging
from unittest.mock import patch

User = get_user_model()

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
    return Bounty.objects.create(
        title="Test Bounty",
        description="This is a test bounty",
        product=product,
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
def cart(db, person, bounty):
    cart = Cart.objects.create(person=person, status=Cart.CartStatus.OPEN)
    cart.items.create(
        bounty=bounty,
        item_type=CartLineItem.ItemType.BOUNTY
    )
    return cart

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
@patch('apps.commerce.models.Cart.total_usd_cents')
def test_successful_bounty_checkout_with_sufficient_balance(mock_total_usd_cents, client, person, organisation, wallet, cart):
    mock_total_usd_cents.return_value = 10000  # $100.00
    client.force_login(person.user)
    wallet.balance_usd_cents = 15000  # $150.00
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
        unit_price_cents=10000,  # Changed to unit_price_cents
        bounty=bounty
    )

    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    response = client.post(reverse('bounty_checkout'))
    assert response.status_code == 302
    assert response.url == reverse('checkout_success')

    sales_order = SalesOrder.objects.get(cart=cart)
    assert sales_order.status == 'Completed'
    assert sales_order.total_usd_cents_excluding_fees_and_taxes == 10000

    wallet.refresh_from_db()
    assert wallet.balance_usd_cents == 5000

@pytest.mark.django_db
@patch('apps.commerce.models.Cart.total_usd_cents')
def test_bounty_checkout_with_wallet_top_up(mock_total_usd_cents, client, person, organisation, wallet, cart):
    mock_total_usd_cents.return_value = 10000  # $100.00
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
        unit_price_cents=10000,  # Changed to unit_price_cents
        bounty=bounty
    )

    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    response = client.post(reverse('bounty_checkout'))
    assert response.status_code == 302
    assert response.url == reverse('wallet_top_up')

    assert not SalesOrder.objects.filter(cart=cart).exists()

    wallet.refresh_from_db()
    assert wallet.balance_usd_cents == 5000

@pytest.mark.django_db
def test_wallet_top_up_failure(client, person, organisation, wallet, cart, monkeypatch):
    client.force_login(person.user)
    wallet.balance_usd_cents = 5000  # $50.00
    wallet.save()
    
    # Associate the person with the organisation
    OrganisationPersonRoleAssignment.objects.create(
        person=person,
        organisation=organisation,
        role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )

    # Create a SalesOrder
    sales_order = SalesOrder.objects.create(cart=cart, organisation=organisation)
    
    # ... (rest of the test case)
