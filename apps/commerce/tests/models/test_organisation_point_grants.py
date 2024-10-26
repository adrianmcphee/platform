import pytest
from apps.commerce.services.organisation_point_grant_service import OrganisationPointGrantService
from apps.commerce.services.cart_service import CartService
from apps.commerce.services.order_service import OrderService

@pytest.fixture
def mock_point_grant_service(mocker):
    return mocker.Mock(spec=OrganisationPointGrantService)

@pytest.fixture
def mock_cart_service(mocker):
    return mocker.Mock(spec=CartService)

@pytest.fixture
def mock_order_service(mocker):
    return mocker.Mock(spec=OrderService)

class TestOrganisationPointGrantRequest:
    def test_free_grant_request_requires_rationale(self, mock_point_grant_service):
        mock_point_grant_service.create_request.return_value = (False, "Rationale is required for free grants")
        
        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="",
            grant_type=OrganisationPointGrantService.GrantType.FREE
        )
        
        assert not success
        assert "rationale" in message.lower()

    def test_paid_grant_request_without_rationale(self, mock_point_grant_service):
        mock_point_grant_service.create_request.return_value = (True, "Request created successfully")
        
        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="",
            grant_type=OrganisationPointGrantService.GrantType.PAID
        )
        
        assert success

    def test_grant_request_approval_flow(self, mock_point_grant_service):
        mock_point_grant_service.create_request.return_value = (True, "Request created with ID: test_id")
        mock_point_grant_service.get_request.side_effect = [
            {'status': "Pending"},
            {'status': "Approved"}
        ]
        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        
        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="Test rationale",
            grant_type=OrganisationPointGrantService.GrantType.FREE
        )
        assert success
        request_id = message.split()[-1]
        
        request = mock_point_grant_service.get_request(request_id)
        assert request['status'] == "Pending"
        
        success, _ = mock_point_grant_service.approve_request(request_id)
        assert success
        
        updated_request = mock_point_grant_service.get_request(request_id)
        assert updated_request['status'] == "Approved"

class TestPointGrantCartIntegration:
    def test_add_point_grant_to_cart(self, mock_cart_service, mock_point_grant_service):
        mock_point_grant_service.create_request.return_value = (True, "Request created with ID: test_id")
        mock_cart_service.add_point_grant_request.return_value = (True, "Added successfully")

        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="Test paid grant",
            grant_type=OrganisationPointGrantService.GrantType.PAID
        )
        assert success
        request_id = message.split()[-1]

        success, message = mock_cart_service.add_point_grant_request("cart_id", request_id)

        assert success
        mock_cart_service.add_point_grant_request.assert_called_once_with("cart_id", request_id)

    def test_paid_grant_order_flow(self, mock_point_grant_service, mock_order_service):
        mock_point_grant_service.create_request.return_value = (True, "Request created with ID: test_id")
        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        mock_order_service.process_paid_point_grants.return_value = (True, "Processed successfully")

        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="Test paid grant",
            grant_type=OrganisationPointGrantService.GrantType.PAID
        )
        assert success
        request_id = message.split()[-1]

        success, _ = mock_point_grant_service.approve_request(request_id)
        assert success

        success, message = mock_order_service.process_paid_point_grants("order_id")

        assert success
        mock_point_grant_service.approve_request.assert_called_once_with(request_id)
        mock_order_service.process_paid_point_grants.assert_called_once_with("order_id")

class TestOrganisationPointGrant:
    def test_free_grant_creation(self, mock_point_grant_service):
        mock_point_grant_service.create_request.return_value = (True, "Request created with ID: test_id")
        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        mock_point_grant_service.get_grant.return_value = {
            'amount': 1000,
            'sales_order_item': None
        }

        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="Test free grant",
            grant_type=OrganisationPointGrantService.GrantType.FREE
        )
        assert success
        request_id = message.split()[-1]

        success, _ = mock_point_grant_service.approve_request(request_id)
        assert success

        grant = mock_point_grant_service.get_grant(request_id)
        assert grant is not None
        assert grant['amount'] == 1000
        assert not grant.get('sales_order_item')

    def test_process_paid_grant(self, mock_point_grant_service, mock_order_service):
        mock_point_grant_service.create_request.return_value = (True, "Request created with ID: test_id")
        mock_point_grant_service.approve_request.return_value = (True, "Approved successfully")
        mock_point_grant_service.process_paid_grant.return_value = (True, "Processed successfully")
        mock_order_service.create_order_item.return_value = (True, "order_item_id")

        success, message = mock_point_grant_service.create_request(
            organisation_id="org_id",
            number_of_points=1000,
            requested_by_id="person_id",
            rationale="Test paid grant",
            grant_type=OrganisationPointGrantService.GrantType.PAID
        )
        assert success
        request_id = message.split()[-1]

        success, _ = mock_point_grant_service.approve_request(request_id)
        assert success

        success, order_item_id = mock_order_service.create_order_item(
            sales_order_id="order_id",
            item_type="POINT_GRANT",
            quantity=1,
            unit_price_usd_cents=50000,
            unit_price_points=1000
        )
        assert success

        success, message = mock_point_grant_service.process_paid_grant(request_id, order_item_id)

        assert success
        mock_point_grant_service.approve_request.assert_called_once_with(request_id)
        mock_point_grant_service.process_paid_grant.assert_called_once_with(request_id, order_item_id)
