import pytest
from django.db import transaction
from apps.commerce.models import Cart, PointOrder, ProductPointAccount, CartLineItem, Organisation
from apps.product_management.models import Bounty, Product
from apps.talent.models import Person
from apps.security.models import User

@pytest.mark.django_db
def test_point_order_completion():
    # Setup
    user = User.objects.create(username="testuser")
    person = Person.objects.create(user=user, full_name="Test User")
    organisation = Organisation.objects.create(name="Test Organisation")
    product = Product.objects.create(name="Test Product", organisation=organisation)
    product_account, _ = ProductPointAccount.objects.get_or_create(
        product=product,
        defaults={'balance': 1000}
    )
    cart = Cart.objects.create(person=person, organisation=organisation)
    bounty = Bounty.objects.create(title="Test Bounty", reward_type='POINTS', reward_in_points=500, product=product)
    
    # Create CartLineItem for the bounty
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_points=500,
        bounty=bounty,
        funding_type='POINTS'
    )

    point_order = PointOrder.objects.create(
        cart=cart,
        product_account=product_account,
        total_points=500
    )

    # Ensure the product account has the correct initial balance
    product_account.balance = 1000
    product_account.save()

    # Test completion
    result = point_order.complete()
    print(f"Completion result: {result}")
    print(f"Point order status: {point_order.status}")
    product_account.refresh_from_db()
    print(f"Product account balance: {product_account.balance}")
    assert result, "Point order completion failed"
    assert point_order.status == "COMPLETED"
    assert product_account.balance == 500

    # Check if the bounty is activated
    bounty.refresh_from_db()
    assert bounty.status == Bounty.BountyStatus.OPEN

@pytest.mark.django_db
def test_point_order_refund():
    # Setup
    user = User.objects.create(username="testuser")
    person = Person.objects.create(user=user, full_name="Test User")
    organisation = Organisation.objects.create(name="Test Organisation")
    product = Product.objects.create(name="Test Product", organisation=organisation)
    product_account, _ = ProductPointAccount.objects.get_or_create(
        product=product,
        defaults={'balance': 1000}
    )
    cart = Cart.objects.create(person=person, organisation=organisation)
    bounty = Bounty.objects.create(title="Test Bounty", reward_type='POINTS', reward_in_points=500, product=product)
    
    # Create CartLineItem for the bounty
    CartLineItem.objects.create(
        cart=cart,
        item_type=CartLineItem.ItemType.BOUNTY,
        quantity=1,
        unit_price_points=500,
        bounty=bounty,
        funding_type='POINTS'
    )

    point_order = PointOrder.objects.create(
        cart=cart,
        product_account=product_account,
        total_points=500,
        status="COMPLETED"
    )

    # Simulate completion of the order (without actually changing the balance)
    bounty.status = Bounty.BountyStatus.OPEN
    bounty.save()

    # Ensure the product account has the correct balance after completion
    product_account.balance = 500
    product_account.save()

    # Test refund
    initial_balance = product_account.balance
    assert point_order.refund()
    product_account.refresh_from_db()
    assert product_account.balance == initial_balance + 500

    # Test that bounty is deactivated
    bounty.refresh_from_db()
    assert bounty.status == Bounty.BountyStatus.DRAFT
