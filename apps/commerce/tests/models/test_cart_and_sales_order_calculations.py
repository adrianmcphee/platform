import pytest
import logging
from apps.commerce.models import Cart, SalesOrder, CartLineItem, Organisation, PlatformFeeConfiguration
from apps.product_management.models import Bounty, Product
from apps.talent.models import Person
from apps.security.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)

@pytest.fixture
def setup_data():
    # Create a User instance
    user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpassword")
    
    # Create a Person instance associated with the User
    person = Person.objects.create(user=user)
    
    organisation = Organisation.objects.create(name="Test Org")
    
    # Create a Product instance
    product = Product.objects.create(name="Test Product", organisation=organisation)
    
    bounty = Bounty.objects.create(
        title="Test Bounty",
        reward_type='USD',
        reward_in_usd_cents=10000,
        product=product
    )

    # Ensure a PlatformFeeConfiguration exists
    PlatformFeeConfiguration.objects.create(
        percentage=5,
        applies_from_date=timezone.now() - timezone.timedelta(days=1)  # Make sure it's active
    )

    cart = Cart.objects.create(person=person, organisation=organisation)
    
    # Ensure the SalesOrder is created with the correct organisation
    sales_order = SalesOrder.objects.get(cart=cart)
    
    logger.info(f"Setup data created: Cart {cart.id}, SalesOrder {sales_order.id}")
    return person, organisation, cart, sales_order, bounty, product

@pytest.mark.django_db
def test_cart_and_sales_order_totals_match(setup_data):
    person, organisation, cart, sales_order, bounty, product = setup_data
    
    logger.info(f"Creating CartLineItems for Cart {cart.id}")
    # Create a bounty line item
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_usd_cents=bounty.reward_in_usd_cents,
        bounty=bounty,
        funding_type=bounty.reward_type
    )

    logger.info(f"Updating totals for Cart {cart.id}")
    cart.update_totals()

    logger.info(f"Refreshing SalesOrder {sales_order.id} from database")
    sales_order.refresh_from_db()

    logger.info(f"Cart {cart.id} totals: excluding fees: {cart.total_usd_cents_excluding_fees_and_taxes}, including fees: {cart.total_usd_cents_including_fees_and_taxes}")
    logger.info(f"SalesOrder {sales_order.id} totals: excluding fees: {sales_order.total_usd_cents_excluding_fees_and_taxes}, including fees: {sales_order.total_usd_cents_including_fees_and_taxes}")

    # Assert that the totals match
    assert cart.total_usd_cents_excluding_fees_and_taxes == sales_order.total_usd_cents_excluding_fees_and_taxes
    assert cart.total_usd_cents_including_fees_and_taxes == sales_order.total_usd_cents_including_fees_and_taxes

    # Check that the platform fee was automatically added
    platform_fee_item = cart.line_items.filter(item_type=CartLineItem.ItemType.PLATFORM_FEE).first()
    assert platform_fee_item is not None

    # Calculate expected fee (5% fee)
    expected_fee = int(bounty.reward_in_usd_cents * 0.05)
    assert platform_fee_item.unit_price_usd_cents == expected_fee

    # Check total calculations
    assert cart.total_usd_cents_excluding_fees_and_taxes == bounty.reward_in_usd_cents
    assert cart.total_usd_cents_including_fees_and_taxes == bounty.reward_in_usd_cents + expected_fee

@pytest.mark.django_db
def test_cart_update_totals_updates_sales_order(setup_data):
    person, organisation, cart, sales_order, bounty, product = setup_data
    
    logger.info(f"Creating CartLineItems for Cart {cart.id}")
    # Create a bounty line item
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_usd_cents=bounty.reward_in_usd_cents,
        bounty=bounty,
        funding_type=bounty.reward_type
    )

    logger.info(f"Updating totals for Cart {cart.id}")
    cart.update_totals()

    logger.info(f"Refreshing SalesOrder {sales_order.id} from database")
    sales_order.refresh_from_db()

    logger.info(f"Cart {cart.id} totals: excluding fees: {cart.total_usd_cents_excluding_fees_and_taxes}, including fees: {cart.total_usd_cents_including_fees_and_taxes}")
    logger.info(f"SalesOrder {sales_order.id} totals: excluding fees: {sales_order.total_usd_cents_excluding_fees_and_taxes}, including fees: {sales_order.total_usd_cents_including_fees_and_taxes}")

    # Assert that the sales order totals have been updated
    assert sales_order.total_usd_cents_excluding_fees_and_taxes == 10000
    assert sales_order.total_usd_cents_including_fees_and_taxes == 10500  # 10000 + 5% fee

    logger.info(f"Updating totals for Cart {cart.id} again")
    cart.update_totals()

    logger.info(f"Refreshing SalesOrder {sales_order.id} from database again")
    sales_order.refresh_from_db()

    logger.info(f"Cart {cart.id} totals: excluding fees: {cart.total_usd_cents_excluding_fees_and_taxes}, including fees: {cart.total_usd_cents_including_fees_and_taxes}")
    logger.info(f"SalesOrder {sales_order.id} totals: excluding fees: {sales_order.total_usd_cents_excluding_fees_and_taxes}, including fees: {sales_order.total_usd_cents_including_fees_and_taxes}")

    # Assert that the sales order totals have not changed
    assert sales_order.total_usd_cents_excluding_fees_and_taxes == 10000
    assert sales_order.total_usd_cents_including_fees_and_taxes == 10500

@pytest.mark.django_db
def test_multiple_bounties_and_fees(setup_data):
    person, organisation, cart, sales_order, bounty, product = setup_data
    
    logger.info(f"Creating first CartLineItem for Cart {cart.id}")
    # Create first bounty line item
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_usd_cents=10000,
        bounty=bounty,
        funding_type='USD'
    )

    logger.info(f"Creating second CartLineItem for Cart {cart.id}")
    # Create second bounty
    second_bounty = Bounty.objects.create(
        title="Second Test Bounty",
        reward_type='USD',
        reward_in_usd_cents=5000,
        product=product  # Use the same product as the first bounty
    )

    # Create second bounty line item
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_usd_cents=5000,
        bounty=second_bounty,
        funding_type='USD'
    )

    logger.info(f"Updating totals for Cart {cart.id}")
    cart.update_totals()

    logger.info(f"Refreshing SalesOrder {sales_order.id} from database")
    sales_order.refresh_from_db()

    logger.info(f"Cart {cart.id} totals: excluding fees: {cart.total_usd_cents_excluding_fees_and_taxes}, including fees: {cart.total_usd_cents_including_fees_and_taxes}")
    logger.info(f"SalesOrder {sales_order.id} totals: excluding fees: {sales_order.total_usd_cents_excluding_fees_and_taxes}, including fees: {sales_order.total_usd_cents_including_fees_and_taxes}")

    # Assert that the totals match
    assert cart.total_usd_cents_excluding_fees_and_taxes == sales_order.total_usd_cents_excluding_fees_and_taxes
    assert cart.total_usd_cents_including_fees_and_taxes == sales_order.total_usd_cents_including_fees_and_taxes

    # Check that the platform fee was automatically added
    platform_fee_item = cart.line_items.filter(item_type=CartLineItem.ItemType.PLATFORM_FEE).first()
    assert platform_fee_item is not None

    # Calculate expected fee (5% of total bounty amount)
    expected_fee = int(15000 * 0.05)
    assert platform_fee_item.unit_price_usd_cents == expected_fee

    # Check total calculations
    assert cart.total_usd_cents_excluding_fees_and_taxes == 15000
    assert cart.total_usd_cents_including_fees_and_taxes == 15000 + expected_fee
