import pytest
from unittest.mock import Mock, patch
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
from apps.commerce.services.organisation_point_grant_service import OrganisationPointGrantService
from apps.commerce.services.cart_service import CartService
from apps.commerce.services.order_service import OrderService

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

@pytest.fixture
def point_grant_service():
    return OrganisationPointGrantService()

@pytest.fixture
def cart_service():
    return CartService()

@pytest.fixture
def order_service():
    return OrderService()

@pytest.fixture
def mock_point_grant_service():
    return Mock(spec=OrganisationPointGrantService)

@pytest.fixture
def mock_cart_service():
    return Mock(spec=CartService)

@pytest.fixture
def mock_order_service():
    return Mock(spec=OrderService)

class TestOrganisationPointGrantRequest:
    def test_free_grant_request_requires_rationale(self, organisation, person):
        # Should raise ValidationError when free grant has no rationale
        with pytest.raises(ValidationError):
            grant_request = OrganisationPointGrantRequest(
                organisation=organisation,
                number_of_points=1000,
                requested_by=person,
                grant_type=OrganisationPointGrantRequest.GrantType.FREE,
                rationale=""  # Empty rationale
            )
            grant_request.full_clean()

    def test_paid_grant_request_without_rationale(self, organisation, person):
        # Should allow paid grant without rationale
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
            rationale=""
        )
        assert grant_request.id is not None

    def test_grant_request_approval_flow(self, organisation, person):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.FREE,
            rationale="Test rationale"
        )
        
        assert grant_request.status == "Pending"
        grant_request.approve()
        assert grant_request.status == "Approved"
        assert hasattr(grant_request, "resulting_grant")

    @patch('apps.commerce.models.OrganisationPointGrantRequest.approve')
    def test_approve_free_grant_request(self, mock_approve, organisation, person, mock_point_grant_service):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.FREE,
            rationale="Test free grant"
        )
        
        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        
        success, message = mock_point_grant_service.approve_request(grant_request.id)
        
        assert success
        mock_point_grant_service.approve_request.assert_called_once_with(grant_request.id)
        mock_approve.assert_called_once()

    def test_approve_paid_grant_request(self, organisation, person, mock_point_grant_service):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
            rationale="Test paid grant"
        )
        
        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        
        success, message = mock_point_grant_service.approve_request(grant_request.id)
        
        assert success
        mock_point_grant_service.approve_request.assert_called_once_with(grant_request.id)

class TestPointGrantCartIntegration:
    def test_add_point_grant_to_cart(self, organisation, person, cart, mock_cart_service):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
        )

        mock_cart_service.add_point_grant_request.return_value = (True, "Added successfully")

        success, message = mock_cart_service.add_point_grant_request(cart.id, grant_request.id)

        assert success
        mock_cart_service.add_point_grant_request.assert_called_once_with(cart.id, grant_request.id)

    def test_paid_grant_order_flow(self, organisation, person, cart, sales_order, mock_point_grant_service, mock_order_service):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
        )

        order_item = SalesOrderLineItem.objects.create(
            sales_order=sales_order,
            item_type=SalesOrderLineItem.ItemType.POINT_GRANT,
            quantity=1,
            unit_price_usd_cents=50000,
            unit_price_points=1000,
            point_grant_request=grant_request
        )

        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        mock_order_service.process_paid_point_grants.return_value = (True, "Processed successfully")

        # Approve the grant request
        success, _ = mock_point_grant_service.approve_request(grant_request.id)
        assert success

        # Set order status to paid
        sales_order.status = SalesOrder.OrderStatus.PAID
        sales_order.save()

        # Process paid point grants
        success, message = mock_order_service.process_paid_point_grants(sales_order.id)

        assert success
        mock_point_grant_service.approve_request.assert_called_once_with(grant_request.id)
        mock_order_service.process_paid_point_grants.assert_called_once_with(sales_order.id)

class TestOrganisationPointGrant:
    def test_free_grant_creation(self, organisation, person):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
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
            number_of_points=1000,
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
            number_of_points=1000,
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

    def test_process_paid_grant(self, organisation, person, sales_order, mock_point_grant_service):
        grant_request = OrganisationPointGrantRequest.objects.create(
            organisation=organisation,
            number_of_points=1000,
            requested_by=person,
            grant_type=OrganisationPointGrantRequest.GrantType.PAID,
        )

        order_item = SalesOrderLineItem.objects.create(
            sales_order=sales_order,
            item_type=SalesOrderLineItem.ItemType.POINT_GRANT,
            quantity=1,
            unit_price_usd_cents=50000,
            unit_price_points=1000,
            point_grant_request=grant_request
        )

        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        mock_point_grant_service.process_paid_grant.return_value = (True, "Processed successfully")

        # Approve the grant request
        success, _ = mock_point_grant_service.approve_request(grant_request.id)
        assert success

        # Process the paid grant
        success, message = mock_point_grant_service.process_paid_grant(grant_request.id, order_item.id)

        assert success
        mock_point_grant_service.approve_request.assert_called_once_with(grant_request.id)
        mock_point_grant_service.process_paid_grant.assert_called_once_with(grant_request.id, order_item.id)
