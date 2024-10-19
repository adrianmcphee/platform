# integration_tests/conftest.py
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.product_management.models import Product, Challenge, Competition, Bounty
from apps.talent.models import BountyBid, BountyClaim, Person
from apps.commerce.models import Organisation

@pytest.fixture
def user():
    User = get_user_model()
    return User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')

@pytest.fixture
def person():
    return Person.objects.create(name="Test User", email="test@example.com")

@pytest.fixture
def organisation():
    return Organisation.objects.create(name="Test Org")

@pytest.fixture
def product():
    return Product.objects.create(name='Test Product')

@pytest.fixture
def challenge(product):
    return Challenge.objects.create(
        product=product,
        title='Test Challenge',
        status=Challenge.ChallengeStatus.DRAFT
    )

@pytest.fixture
def competition(product):
    return Competition.objects.create(
        product=product,
        title='Test Competition',
        status=Competition.CompetitionStatus.DRAFT
    )

@pytest.fixture
def bounty(challenge):
    return Bounty.objects.create(
        challenge=challenge,
        title='Test Bounty',
        reward_amount=100,
        reward_type='USD'
    )

@pytest.fixture
def bounty_bid(bounty, person):
    return BountyBid.objects.create(
        bounty=bounty,
        person=person,
        amount=100,
        expected_finish_date=timezone.now().date() + timezone.timedelta(days=7)
    )

@pytest.fixture
def bounty_claim(bounty, person, bounty_bid):
    return BountyClaim.objects.create(
        bounty=bounty,
        person=person,
        accepted_bid=bounty_bid
    )
