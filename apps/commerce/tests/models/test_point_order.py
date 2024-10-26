import pytest
from unittest.mock import Mock, patch
from apps.commerce.services.organisation_point_grant_service import OrganisationPointGrantService
from apps.commerce.services.cart_service import CartService
from apps.commerce.services.order_service import OrderService

@pytest.fixture
def mock_point_grant_service():
    return Mock(spec=OrganisationPointGrantService)

@pytest.fixture
def mock_cart_service():
    return Mock(spec=CartService)

@pytest.fixture
def mock_order_service():
    return Mock(spec=OrderService)

@pytest.fixture
def setup_data(mock_point_grant_service, mock_cart_service, mock_order_service):
    # Mock data
    mock_user_id = "user_123"
    mock_person_id = "person_123"
    mock_organisation_id = "org_123"
    mock_product_id = "product_123"
    mock_cart_id = "cart_123"
    mock_bounty_id = "bounty_123"
    mock_order_id = "order_123"
    mock_grant_request_id = "grant_request_123"

    # Mock point grant service methods
    mock_point_grant_service.create_request.return_value = (True, f"Request created with ID: {mock_grant_request_id}")
    mock_point_grant_service.approve_request.return_value = (True, "Request approved")
    mock_point_grant_service.process_paid_grant.return_value = (True, "Paid grant processed")

    # Mock cart service methods
    mock_cart_service.create_cart.return_value = (True, mock_cart_id)
    mock_cart_service.add_point_grant_request.return_value = (True, "Point grant request added to cart")
    mock_cart_service.update_totals.return_value = (True, "Cart totals updated")

    # Mock order service methods
    mock_order_service.create_from_cart.return_value = (True, mock_order_id)
    mock_order_service.process_payment.return_value = (True, "Payment processed")
    mock_order_service.process_paid_point_grants.return_value = (True, "Paid point grants processed")

    return {
        'user_id': mock_user_id,
        'person_id': mock_person_id,
        'organisation_id': mock_organisation_id,
        'product_id': mock_product_id,
        'cart_id': mock_cart_id,
        'bounty_id': mock_bounty_id,
        'order_id': mock_order_id,
        'grant_request_id': mock_grant_request_id,
    }

def test_point_order_completion(setup_data, mock_point_grant_service, mock_cart_service, mock_order_service):
    # Create point grant request
    success, message = mock_point_grant_service.create_request(
        organisation_id=setup_data['organisation_id'],
        number_of_points=500,
        requested_by_id=setup_data['person_id'],
        rationale="Test paid grant",
        grant_type=OrganisationPointGrantService.GrantType.PAID
    )
    assert success
    grant_request_id = message.split()[-1]

    # Create cart and add point grant request
    success, cart_id = mock_cart_service.create_cart(setup_data['person_id'], setup_data['organisation_id'])
    assert success
    success, _ = mock_cart_service.add_point_grant_request(cart_id, grant_request_id)
    assert success
    success, _ = mock_cart_service.update_totals(cart_id)
    assert success

    # Create order from cart
    success, order_id = mock_order_service.create_from_cart(cart_id)
    assert success

    # Process payment
    success, _ = mock_order_service.process_payment(order_id)
    assert success

    # Process paid point grants
    success, _ = mock_order_service.process_paid_point_grants(order_id)
    assert success

    # Verify that the point grant was processed
    mock_point_grant_service.process_paid_grant.assert_called_once_with(grant_request_id, mock.ANY)

def test_point_order_refund(setup_data, mock_point_grant_service, mock_cart_service, mock_order_service):
    # Create point grant request
    success, message = mock_point_grant_service.create_request(
        organisation_id=setup_data['organisation_id'],
        number_of_points=500,
        requested_by_id=setup_data['person_id'],
        rationale="Test paid grant",
        grant_type=OrganisationPointGrantService.GrantType.PAID
    )
    assert success
    grant_request_id = message.split()[-1]

    # Create cart and add point grant request
    success, cart_id = mock_cart_service.create_cart(setup_data['person_id'], setup_data['organisation_id'])
    assert success
    success, _ = mock_cart_service.add_point_grant_request(cart_id, grant_request_id)
    assert success
    success, _ = mock_cart_service.update_totals(cart_id)
    assert success

    # Create order from cart
    success, order_id = mock_order_service.create_from_cart(cart_id)
    assert success

    # Process payment
    success, _ = mock_order_service.process_payment(order_id)
    assert success

    # Process paid point grants
    success, _ = mock_order_service.process_paid_point_grants(order_id)
    assert success

    # Mock refund methods
    mock_order_service.refund_order = Mock(return_value=(True, "Order refunded"))
    mock_point_grant_service.revoke_grant = Mock(return_value=(True, "Grant revoked"))

    # Refund the order
    success, _ = mock_order_service.refund_order(order_id)
    assert success

    # Verify that the point grant was revoked
    mock_point_grant_service.revoke_grant.assert_called_once_with(mock.ANY)
