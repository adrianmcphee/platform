import pytest
from decimal import Decimal

from apps.commerce.services.cart_service import CartService
from apps.commerce.services.sales_order_service import SalesOrderService
from apps.commerce.services.tax_service import TaxService
from apps.commerce.services.fee_service import FeeService
from apps.commerce.services.contributor_wallet_service import ContributorWalletService
from apps.commerce.services.organisation_wallet_service import OrganisationWalletService
from apps.product_management.services.bounty_service import BountyService
from apps.common.data_transfer_objects import BountyPurchaseData, RewardType, BountyStatus

@pytest.fixture
def mock_tax_service(mocker):
    return mocker.Mock(spec=TaxService)

@pytest.fixture
def mock_fee_service(mocker):
    return mocker.Mock(spec=FeeService)

@pytest.fixture
def mock_contributor_wallet_service(mocker):
    mock = mocker.Mock(spec=ContributorWalletService)
    mock.get_balance.return_value = 20000  # $200.00
    mock.add_funds.return_value = (True, "Funds added successfully")
    return mock

@pytest.fixture
def mock_organisation_wallet_service(mocker):
    mock = mocker.Mock(spec=OrganisationWalletService)
    mock.get_balance.return_value = 100000  # $1000.00
    mock.deduct_funds.return_value = (True, "Funds deducted successfully")
    return mock

@pytest.fixture
def mock_bounty_service(mocker):
    mock = mocker.Mock(spec=BountyService)
    mock.get_bounty.side_effect = lambda product_id: {
        "test_product_id": {
            "id": "2ZEH9Uh6Yt7KPz8LCNRJ1q",
            "reward_type": "USD",
            "reward_in_usd_cents": 10000
        },
        "test_point_product_id": {
            "id": "3FGK0Vj7Zs8MPa9MDPQN2r",
            "reward_type": "POINTS",
            "reward_in_points": 500
        },
        "usd_product_id": {
            "id": "4HLM1Wk8At9NQb0NEPRO3s",
            "reward_type": "USD",
            "reward_in_usd_cents": 10000
        },
        "point_product_id": {
            "id": "5JNO2Xl9Bu0PRc1OFQSP4t",
            "reward_type": "POINTS",
            "reward_in_points": 500
        }
    }[product_id]
    return mock

@pytest.fixture
def cart_service(mock_tax_service, mock_fee_service):
    return CartService(tax_service=mock_tax_service, fee_service=mock_fee_service)

@pytest.fixture
def order_service(mock_contributor_wallet_service, mock_organisation_wallet_service):
    return SalesOrderService(
        contributor_wallet_service=mock_contributor_wallet_service,
        organisation_wallet_service=mock_organisation_wallet_service
    )

def test_add_bounty_to_cart(cart_service, mock_bounty_service):
    cart_id = "1YDG8Tj5Xs6LPa7JBMNK0p"
    bounty_id = "test_bounty_id"
    
    cart_service.add_bounty(cart_id, bounty_id, mock_bounty_service)
    
    cart = cart_service.get_cart(cart_id)
    assert len(cart['line_items']) == 1
    assert cart['line_items'][0]['item_type'] == 'BOUNTY'
    assert cart['line_items'][0]['unit_price_usd_cents'] == 10000
    assert cart['line_items'][0]['metadata']['product_id'] == "2ZEH9Uh6Yt7KPz8LCNRJ1q"

def test_add_point_bounty_to_cart(cart_service, mock_bounty_service):
    cart_id = "2ZEH9Uh6Yt7KPz8LCNRJ1q"
    bounty_id = "test_point_bounty_id"
    
    cart_service.add_bounty(cart_id, bounty_id, mock_bounty_service)
    
    cart = cart_service.get_cart(cart_id)
    assert len(cart['line_items']) == 1
    assert cart['line_items'][0]['item_type'] == 'BOUNTY'
    assert cart['line_items'][0]['unit_price_points'] == 500
    assert cart['line_items'][0]['item_id'] == "3FGK0Vj7Zs8MPa9MDPQN2r"

def test_successful_bounty_checkout(cart_service, order_service, mock_bounty_service, mock_organisation_wallet_service):
    cart_id = "3FGK0Vj7Zs8MPa9MDPQN2r"
    bounty_id = "test_bounty_id"
    organisation_wallet_id = "6KMP3Ym0Cv1QRd2PGQTO5u"
    
    cart_service.add_bounty(cart_id, bounty_id, mock_bounty_service)
    cart_service.update_totals(cart_id)
    
    order_id = order_service.create_from_cart(cart_id)
    success = order_service.process_payment(order_id, organisation_wallet_id)
    
    assert success
    mock_organisation_wallet_service.deduct_funds.assert_called_once()
    
    order = order_service.get_order(order_id)
    assert order['status'] == 'COMPLETED'

def test_bounty_checkout_insufficient_funds(cart_service, order_service, mock_bounty_service, mock_organisation_wallet_service):
    cart_id = "4HLM1Wk8At9NQb0NEPRO3s"
    bounty_id = "test_bounty_id"
    organisation_wallet_id = "7LNQ4Zn1Dw2RSe3QHRUP6v"
    
    mock_organisation_wallet_service.get_balance.return_value = 5000  # $50.00
    mock_organisation_wallet_service.deduct_funds.return_value = (False, "Insufficient funds")
    
    cart_service.add_bounty(cart_id, bounty_id, mock_bounty_service)
    cart_service.update_totals(cart_id)
    
    order_id = order_service.create_from_cart(cart_id)
    success = order_service.process_payment(order_id, organisation_wallet_id)
    
    assert not success
    mock_organisation_wallet_service.deduct_funds.assert_called_once()
    
    order = order_service.get_order(order_id)
    assert order['status'] == 'PAYMENT_FAILED'

def test_mixed_currency_bounty_cart(cart_service, mock_bounty_service):
    cart_id = "5JNO2Xl9Bu0PRc1OFQSP4t"
    usd_bounty_id = "usd_bounty_id"
    point_bounty_id = "point_bounty_id"
    
    cart_service.add_bounty(cart_id, usd_bounty_id, mock_bounty_service)
    cart_service.add_bounty(cart_id, point_bounty_id, mock_bounty_service)
    cart_service.update_totals(cart_id)
    
    cart = cart_service.get_cart(cart_id)
    
    assert len(cart['line_items']) == 2
    assert any(
        item['metadata']['reward_type'] == 'USD' and 
        item['unit_price_usd_cents'] == 10000 and 
        item['metadata']['product_id'] == "4HLM1Wk8At9NQb0NEPRO3s" 
        for item in cart['line_items']
    )
    assert any(
        item['metadata']['reward_type'] == 'POINTS' and 
        item['unit_price_points'] == 500 and 
        item['metadata']['product_id'] == "5JNO2Xl9Bu0PRc1OFQSP4t" 
        for item in cart['line_items']
    )

def test_successful_point_bounty_checkout(cart_service, order_service, mock_bounty_service, mock_organisation_point_account):
    cart_id = "8MOR5Zn2Ew3TSf4RISUP7w"
    product_id = "test_point_product_id"
    organisation_id = "9NPQ5Aa3Fx4UTg5SJTVQ8x"
    
    cart_service.add_bounty(cart_id, product_id, mock_bounty_service)
    cart_service.update_totals(cart_id)
    
    order_id = order_service.create_from_cart(cart_id)
    success = order_service.process_payment(order_id, organisation_id)
    
    assert success
    mock_organisation_point_account.deduct_points.assert_called_once()
    
    order = order_service.get_order(order_id)
    assert order['status'] == 'COMPLETED'

def test_add_bounty_to_cart():
    bounty_data = BountyPurchaseData(
        id="2ZEH9Uh6Yt7KPz8LCNRJ1q",
        product_id="test_product_id",
        title="Test Bounty",
        description="Test Description",
        reward_type=RewardType.USD,
        reward_in_usd_cents=10000,
        status=BountyStatus.DRAFT
    )
    
    success, message = cart_service.add_bounty("test_cart_id", bounty_data)
    assert success
    assert message == "Item added to cart"
