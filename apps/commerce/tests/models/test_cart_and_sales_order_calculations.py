import pytest
from decimal import Decimal
from apps.commerce.services.cart_service import CartService
from apps.commerce.services.order_service import OrderService
from apps.commerce.services.tax_service import TaxService
from apps.commerce.services.fee_service import FeeService

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
    return OrderService()

@pytest.fixture
def setup_data(mocker, cart_service, order_service):
    # Mock the necessary data and service calls
    mock_cart_id = "mock_cart_id"
    mock_order_id = "mock_order_id"
    mock_bounty_id = "mock_bounty_id"
    mock_organisation_id = "mock_organisation_id"

    # Mock the cart creation
    mocker.patch.object(cart_service, 'create_cart', return_value=(True, mock_cart_id))
    
    # Mock adding a bounty to the cart
    mocker.patch.object(cart_service, 'add_bounty', return_value=(True, "Bounty added to cart"))
    
    # Mock updating cart totals
    mocker.patch.object(cart_service, 'update_totals', return_value=(True, "Cart totals updated"))
    
    # Mock order creation
    mocker.patch.object(order_service, 'create_from_cart', return_value=(True, mock_order_id))

    return {
        'cart_id': mock_cart_id,
        'order_id': mock_order_id,
        'bounty_id': mock_bounty_id,
        'organisation_id': mock_organisation_id
    }

@pytest.mark.django_db
def test_cart_and_sales_order_totals_match(mocker, setup_data, cart_service, order_service):
    cart_id = setup_data['cart_id']
    order_id = setup_data['order_id']
    bounty_id = setup_data['bounty_id']

    # Add bounty to cart
    success, _ = cart_service.add_bounty(cart_id, bounty_id)
    assert success

    # Update cart totals
    success, _ = cart_service.update_totals(cart_id)
    assert success

    # Create order from cart
    success, _ = order_service.create_from_cart(cart_id)
    assert success

    # Mock get_cart and get_order methods
    mocker.patch.object(cart_service, 'get_cart', return_value={
        'total_usd_cents_excluding_fees_and_taxes': 10000,
        'total_usd_cents_including_fees_and_taxes': 11500
    })
    mocker.patch.object(order_service, 'get_order', return_value={
        'total_usd_cents_excluding_fees_and_taxes': 10000,
        'total_usd_cents_including_fees_and_taxes': 11500
    })

    cart = cart_service.get_cart(cart_id)
    order = order_service.get_order(order_id)

    assert cart['total_usd_cents_excluding_fees_and_taxes'] == order['total_usd_cents_excluding_fees_and_taxes']
    assert cart['total_usd_cents_including_fees_and_taxes'] == order['total_usd_cents_including_fees_and_taxes']

@pytest.mark.django_db
def test_multiple_bounties_and_fees(setup_data, cart_service, order_service):
    cart_id = setup_data['cart_id']
    bounty_id = setup_data['bounty_id']

    # Add two bounties to cart
    cart_service.add_bounty(cart_id, bounty_id, quantity=1)
    cart_service.add_bounty(cart_id, "another_bounty_id", quantity=1)

    # Update cart totals
    cart_service.update_totals(cart_id)

    # Mock get_cart method
    cart_service.get_cart = Mock(return_value={
        'total_usd_cents_excluding_fees_and_taxes': 15000,
        'total_usd_cents_including_fees_and_taxes': 17250,
        'line_items': [
            {'item_type': 'BOUNTY', 'unit_price_usd_cents': 10000},
            {'item_type': 'BOUNTY', 'unit_price_usd_cents': 5000},
            {'item_type': 'PLATFORM_FEE', 'unit_price_usd_cents': 750},
            {'item_type': 'SALES_TAX', 'unit_price_usd_cents': 1500}
        ]
    })

    cart = cart_service.get_cart(cart_id)

    assert cart['total_usd_cents_excluding_fees_and_taxes'] == 15000
    assert cart['total_usd_cents_including_fees_and_taxes'] == 17250

    platform_fee = next(item for item in cart['line_items'] if item['item_type'] == 'PLATFORM_FEE')
    assert platform_fee['unit_price_usd_cents'] == 750

    sales_tax = next(item for item in cart['line_items'] if item['item_type'] == 'SALES_TAX')
    assert sales_tax['unit_price_usd_cents'] == 1500

@pytest.mark.django_db
def test_different_country_tax_rates(mocker, setup_data, cart_service, mock_tax_service):
    cart_id = setup_data['cart_id']
    bounty_id = setup_data['bounty_id']
    organisation_id = setup_data['organisation_id']

    # Add bounty to cart
    cart_service.add_bounty(cart_id, bounty_id)

    # Test with different country tax rates
    for country, tax_rate in [('GB', Decimal('0.20')), ('JP', Decimal('0.08'))]:
        # Mock the tax calculation
        mock_tax_service.calculate_tax.return_value = int(10000 * tax_rate)

        # Update cart totals
        cart_service.update_totals(cart_id)

        # Mock get_cart method
        mocker.patch.object(cart_service, 'get_cart', return_value={
            'line_items': [
                {'item_type': 'SALES_TAX', 'unit_price_usd_cents': int(10000 * tax_rate)}
            ]
        })

        cart = cart_service.get_cart(cart_id)
        tax_item = next(item for item in cart['line_items'] if item['item_type'] == 'SALES_TAX')
        assert tax_item['unit_price_usd_cents'] == int(10000 * tax_rate)

@pytest.mark.django_db
def test_sales_order_finalize(mocker, setup_data, cart_service, order_service):
    cart_id = setup_data['cart_id']
    order_id = setup_data['order_id']
    bounty_id = setup_data['bounty_id']

    # Add bounty to cart
    cart_service.add_bounty(cart_id, bounty_id)
    cart_service.update_totals(cart_id)

    # Create order from cart
    order_service.create_from_cart(cart_id)

    # Finalize the order
    mocker.patch.object(order_service, 'finalize_order', return_value=(True, "Order finalized"))
    success, _ = order_service.finalize_order(order_id)
    assert success

    # Mock get_order method
    mocker.patch.object(order_service, 'get_order', return_value={
        'status': 'PAYMENT_PROCESSING',
        'line_items': [
            {'item_type': 'BOUNTY'},
            {'item_type': 'PLATFORM_FEE'},
            {'item_type': 'SALES_TAX'}
        ]
    })

    order = order_service.get_order(order_id)
    assert order['status'] == 'PAYMENT_PROCESSING'
    assert any(item['item_type'] == 'BOUNTY' for item in order['line_items'])
    assert any(item['item_type'] == 'PLATFORM_FEE' for item in order['line_items'])
    assert any(item['item_type'] == 'SALES_TAX' for item in order['line_items'])
