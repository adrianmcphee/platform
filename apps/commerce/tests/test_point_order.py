import pytest
from apps.commerce.services.organisation_point_grant_service import OrganisationPointGrantService
from apps.commerce.services.cart_service import CartService
from apps.commerce.services.sales_order_service import SalesOrderService

@pytest.fixture
def mock_point_grant_service(mocker):
    return mocker.Mock(spec=OrganisationPointGrantService)

@pytest.fixture
def mock_cart_service(mocker):
    return mocker.Mock(spec=CartService)

@pytest.fixture
def mock_order_service(mocker):
    return mocker.Mock(spec=SalesOrderService)

@pytest.fixture
def setup_data(mock_point_grant_service, mock_cart_service, mock_order_service):
    # Mock data using Base58UUIDv5Field format
    mock_user_id = "8HkGVbQnML1cFMZtYNDYj8"
    mock_person_id = "2ZYmfqLJWFJdQazXkvsT7M"
    mock_organisation_id = "4RxVKqP9NLGJb1QzHmCeWS"
    mock_product_id = "6TnFcXwRkMZyD3PsLgAh2Y"
    mock_cart_id = "3JmBvNpWqKLfS7RxTgDc5H"
    mock_bounty_id = "5GkDrYtXnPQcF8ZsVfBh1L"
    mock_order_id = "7LmNwRtYpKJdB9XzCqFg3S"
    mock_grant_request_id = "9PkMvBtWnLJcR7XzFgDh2Q"

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
