import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.commerce.models import (
    OrganisationPointGrant,
    OrganisationPointGrantRequest,
    CartLineItem,
    SalesOrderLineItem,
    Organisation,
    Cart,
    SalesOrder,
)
from apps.talent.models import Person

@pytest.fixture
def organisation():
    return Organisation.objects.create(
        name="Test Org",
        username="testorg",
    )

@pytest.fixture
def person():
    return Person.objects.create(
        username="testuser",
        email="test@example.com"
    )

@pytest.fixture
def cart(organisation, person):
    return Cart.objects.create(
        organisation=organisation,
        person=person,
        country="US"
    )

@pytest.fixture
def sales_order(cart):
    return SalesOrder.objects.create(
        cart=cart,
        organisation=cart.organisation,
    )

class TestOrganisationPointGrantRequest:
    def test_free_grant_request_requires_rationale(self, organisation, person):
        # Should raise ValidationError when free grant has no rationale
        with pytest.raises(ValidationError):
            grant_request = OrganisationPointGrantRequest(
                organisation=organisation,
                amount_points=1000,
                requested_by=person,
                grant_type=OrganisationPointGrantRequest.GrantType.FREE,
                rationale=""  # Empty rationale
            )
            grant_request.full_clean()

    def test_paid_grant_request_without_rationale(self, organisation, person):
        # Should allow paid grant without rationale
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
            rationale=""
        )
        assert grant_request.id is not None

    def test_grant_request_approval_flow(self, organisation, person):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.FREE,
            rationale="Test rationale"
        )
        
        assert grant_request.status == "Pending"
        grant_request.approve()
        assert grant_request.status == "Approved"
        assert hasattr(grant_request, "resulting_grant")

class TestPointGrantCartIntegration:
    def test_add_point_grant_to_cart(self, organisation, person, cart):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
        )

        cart_item = CartLineItem.objects.create(
            cart=cart,
            item_type=CartLineItem.ItemType.POINT_GRANT,
            quantity=1,
            unit_price_usd_cents=50000,  # $500.00
            unit_price_points=1000,
            point_grant_request=grant_request
        )

        assert cart.line_items.count() == 1
        assert cart.line_items.first().point_grant_request == grant_request

    def test_paid_grant_order_flow(self, organisation, person, cart, sales_order):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
        )

        # Add to cart
        cart_item = CartLineItem.objects.create(
            cart=cart,
            item_type=CartLineItem.ItemType.POINT_GRANT,
            quantity=1,
            unit_price_usd_cents=50000,
            unit_price_points=1000,
            point_grant_request=grant_request
        )

        # Create order item
        order_item = SalesOrderLineItem.objects.create(
            sales_order=sales_order,
            item_type=SalesOrderLineItem.ItemType.POINT_GRANT,
            quantity=1,
            unit_price_usd_cents=50000,
            unit_price_points=1000,
            point_grant_request=grant_request
        )

        # Create grant after successful payment
        grant = OrganisationPointGrant.objects.create(
            organisation=organisation,
            amount=1000,
            granted_by=person,
            grant_request=grant_request,
            sales_order_item=order_item
        )

        assert grant.is_paid_grant
        assert grant.sales_order_item == order_item
        assert grant.grant_request == grant_request

class TestOrganisationPointGrant:
    def test_free_grant_creation(self, organisation, person):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.FREE,
            rationale="Test free grant"
        )

        grant = OrganisationPointGrant.objects.create(
            organisation=organisation,
            amount=1000,
            granted_by=person,
            grant_request=grant_request
        )

        assert not grant.is_paid_grant
        assert grant.sales_order_item is None

    def test_paid_vs_free_grant_distinction(self, organisation, person, sales_order):
        # Create free grant
        free_grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.FREE,
            rationale="Test free grant"
        )

        free_grant = OrganisationPointGrant.objects.create(
            organisation=organisation,
            amount=1000,
            granted_by=person,
            grant_request=free_grant_request
        )

        # Create paid grant
        paid_grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            amount_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
        )

        order_item = SalesOrderLineItem.objects.create(
            sales_order=sales_order,
            item_type=SalesOrderLineItem.ItemType.POINT_GRANT,
            quantity=1,
            unit_price_usd_cents=50000,
            unit_price_points=1000,
            point_grant_request=paid_grant_request
        )

        paid_grant = OrganisationPointGrant.objects.create(
            organisation=organisation,
            amount=1000,
            granted_by=person,
            grant_request=paid_grant_request,
            sales_order_item=order_item
        )

        assert not free_grant.is_paid_grant
        assert paid_grant.is_paid_grant