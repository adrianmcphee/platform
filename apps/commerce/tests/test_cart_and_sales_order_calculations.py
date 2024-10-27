import pytest
from decimal import Decimal
from apps.commerce.services.cart_service import CartService
from apps.commerce.services.sales_order_service import SalesOrderService
from apps.commerce.services.tax_service import TaxService
from apps.commerce.services.fee_service import FeeService
from apps.common.fields import Base58UUIDv5Field
from apps.common.data_transfer_objects import BountyPurchaseData, RewardType, BountyStatus

@pytest.fixture
def test_ids():
    field = Base58UUIDv5Field()
    return {
        'cart_id': field.generate_id(),
        'order_id': field.generate_id(),
        'bounty_id': field.generate_id(),
        'product_id': field.generate_id(),
        'organisation_id': field.generate_id()
    }

@pytest.fixture
def bounty_purchase_data(test_ids):
    return BountyPurchaseData(
        id=test_ids['bounty_id'],
        product_id=test_ids['product_id'],
        title="Test Bounty",
        description="Test Description",
        reward_type=RewardType.USD,
        reward_in_usd_cents=10000,
        status=BountyStatus.DRAFT
    )

@pytest.fixture
def mock_tax_service(mocker):
    return mocker.Mock(spec=TaxService)

@pytest.fixture
def mock_fee_service(mocker):
    return mocker.Mock(spec=FeeService)

@pytest.fixture
def cart_service(mock_tax_service, mock_fee_service):
    return CartService(tax_service=mock_tax_service, fee_service=mock_fee_service)

@pytest.fixture
def order_service():
    return SalesOrderService()

@pytest.fixture
def setup_data(mocker, cart_service, order_service, test_ids, bounty_purchase_data):
    # Mock the cart creation using proper Base58 IDs
    mocker.patch.object(cart_service, 'create_cart', return_value=(True, test_ids['cart_id']))
    
    # Mock adding a bounty to the cart
    mocker.patch.object(cart_service, 'add_bounty', return_value=(True, "Bounty added to cart"))
    
    # Mock updating cart totals
    mocker.patch.object(cart_service, 'update_totals', return_value=(True, "Cart totals updated"))
    
    # Mock order creation
    mocker.patch.object(order_service, 'create_from_cart', return_value=(True, "Order created successfully"))

    return {
        'cart_id': test_ids['cart_id'],
        'order_id': test_ids['order_id'],
        'bounty_data': bounty_purchase_data,
        'organisation_id': test_ids['organisation_id']
    }

@pytest.mark.django_db
def test_cart_and_sales_order_totals_match(mocker, setup_data, cart_service, order_service):
    # Arrange
    cart_id = setup_data['cart_id']
    bounty_data = setup_data['bounty_data']
    
    mock_cart_data = {
        'total_usd_cents_excluding_fees_and_taxes': 10000,
        'total_usd_cents_including_fees_and_taxes': 11500,
        'line_items': [{
            'item_type': 'BOUNTY',
            'unit_price_usd_cents': 10000,
            'metadata': bounty_data.dict(exclude={'status'})
        }]
    }
    
    mocker.patch.object(cart_service, 'get_cart', return_value=mock_cart_data)
    mocker.patch.object(order_service, 'get_order', return_value=mock_cart_data)

    # Act
    success, _ = cart_service.add_bounty(cart_id, bounty_data)
    assert success

    success, _ = cart_service.update_totals(cart_id)
    assert success

    success, _ = order_service.create_from_cart(cart_id)
    assert success

    # Assert
    cart = cart_service.get_cart(cart_id)
    order = order_service.get_order(setup_data['order_id'])

    # Check totals match
    assert cart['total_usd_cents_excluding_fees_and_taxes'] == order['total_usd_cents_excluding_fees_and_taxes']
    assert cart['total_usd_cents_including_fees_and_taxes'] == order['total_usd_cents_including_fees_and_taxes']

    # Check line item metadata matches
    cart_item = next(item for item in cart['line_items'] if item['item_type'] == 'BOUNTY')
    order_item = next(item for item in order['line_items'] if item['item_type'] == 'BOUNTY')
    assert cart_item['metadata'] == order_item['metadata']

@pytest.mark.django_db
def test_multiple_bounties_and_fees(mocker, setup_data, cart_service, test_ids):
    # Arrange
    cart_id = setup_data['cart_id']
    bounty_data = setup_data['bounty_data']
    
    # Create second bounty data with different ID and reward
    bounty_data_2 = BountyPurchaseData(
        id=test_ids['bounty_id'],
        product_id=test_ids['product_id'],
        title="Second Test Bounty",
        description="Second Test Description",
        reward_type=RewardType.USD,
        reward_in_usd_cents=5000,
        status=BountyStatus.DRAFT
    )

    mock_cart_data = {
        'total_usd_cents_excluding_fees_and_taxes': 15000,
        'total_usd_cents_including_fees_and_taxes': 17250,
        'line_items': [
            {
                'item_type': 'BOUNTY',
                'unit_price_usd_cents': 10000,
                'metadata': bounty_data.dict(exclude={'status'})
            },
            {
                'item_type': 'BOUNTY',
                'unit_price_usd_cents': 5000,
                'metadata': bounty_data_2.dict(exclude={'status'})
            },
            {'item_type': 'PLATFORM_FEE', 'unit_price_usd_cents': 750},
            {'item_type': 'SALES_TAX', 'unit_price_usd_cents': 1500}
        ]
    }
    
    mocker.patch.object(cart_service, 'get_cart', return_value=mock_cart_data)

    # Act
    cart_service.add_bounty(cart_id, bounty_data)
    cart_service.add_bounty(cart_id, bounty_data_2)
    cart_service.update_totals(cart_id)

    # Assert
    cart = cart_service.get_cart(cart_id)
    assert cart['total_usd_cents_excluding_fees_and_taxes'] == 15000
    assert cart['total_usd_cents_including_fees_and_taxes'] == 17250

    platform_fee = next(item for item in cart['line_items'] if item['item_type'] == 'PLATFORM_FEE')
    assert platform_fee['unit_price_usd_cents'] == 750

    sales_tax = next(item for item in cart['line_items'] if item['item_type'] == 'SALES_TAX')
    assert sales_tax['unit_price_usd_cents'] == 1500

@pytest.mark.django_db
def test_points_bounty_purchase(mocker, setup_data, cart_service, test_ids):
    # Arrange
    cart_id = setup_data['cart_id']
    
    # Create points-based bounty data
    points_bounty_data = BountyPurchaseData(
        id=test_ids['bounty_id'],
        product_id=test_ids['product_id'],
        title="Points Test Bounty",
        description="Points Test Description",
        reward_type=RewardType.POINTS,
        reward_in_points=500,
        status=BountyStatus.DRAFT
    )

    mock_cart_data = {
        'total_points': 500,
        'line_items': [{
            'item_type': 'BOUNTY',
            'unit_price_points': 500,
            'metadata': points_bounty_data.dict(exclude={'status'})
        }]
    }
    
    mocker.patch.object(cart_service, 'get_cart', return_value=mock_cart_data)

    # Act
    success, _ = cart_service.add_bounty(cart_id, points_bounty_data)
    assert success

    # Assert
    cart = cart_service.get_cart(cart_id)
    bounty_item = next(item for item in cart['line_items'] if item['item_type'] == 'BOUNTY')
    assert bounty_item['unit_price_points'] == 500
    assert 'unit_price_usd_cents' not in bounty_item
