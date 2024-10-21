import pytest
from apps.product_management.models import Product
from apps.security.models import ProductRoleAssignment, OrganisationPersonRoleAssignment, User
from apps.talent.models import Person
from apps.commerce.models import Organisation

@pytest.fixture
def setup_data():
    org = Organisation.objects.create(name="Test Org")
    product = Product.objects.create(name="Test Product", organisation=org)
    
    user1 = User.objects.create(username="user1")
    user2 = User.objects.create(username="user2")
    user3 = User.objects.create(username="user3")
    
    person1 = Person.objects.create(full_name="Person 1", preferred_name="P1", user=user1)
    person2 = Person.objects.create(full_name="Person 2", preferred_name="P2", user=user2)
    person3 = Person.objects.create(full_name="Person 3", preferred_name="P3", user=user3)

    OrganisationPersonRoleAssignment.objects.create(
        person=person1, organisation=org, role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
    )
    ProductRoleAssignment.objects.create(
        person=person2, product=product, role=ProductRoleAssignment.ProductRoles.MEMBER
    )

    return {
        'org': org,
        'product': product,
        'person1': person1,
        'person2': person2,
        'person3': person3,
    }

def test_global_visibility(setup_data):
    product = setup_data['product']
    product.visibility = Product.Visibility.GLOBAL
    product.save()
    
    assert product.is_visible_to(setup_data['person1'])
    assert product.is_visible_to(setup_data['person2'])
    assert product.is_visible_to(setup_data['person3'])

def test_org_only_visibility(setup_data):
    product = setup_data['product']
    product.visibility = Product.Visibility.ORG_ONLY
    product.save()
    
    assert product.is_visible_to(setup_data['person1'])
    assert not product.is_visible_to(setup_data['person2'])
    assert not product.is_visible_to(setup_data['person3'])

def test_restricted_visibility(setup_data):
    product = setup_data['product']
    product.visibility = Product.Visibility.RESTRICTED
    product.save()
    
    assert not product.is_visible_to(setup_data['person1'])
    assert product.is_visible_to(setup_data['person2'])
    assert not product.is_visible_to(setup_data['person3'])

def test_manager_permissions(setup_data):
    product = setup_data['product']
    person1 = setup_data['person1']
    person2 = setup_data['person2']
    
    ProductRoleAssignment.objects.create(
        person=person1, product=product, role=ProductRoleAssignment.ProductRoles.MANAGER
    )
    
    assert product.can_manage(person1)
    assert not product.can_manage(person2)
    assert not product.can_admin(person1)

def test_admin_permissions(setup_data):
    product = setup_data['product']
    person1 = setup_data['person1']
    person2 = setup_data['person2']
    
    ProductRoleAssignment.objects.create(
        person=person1, product=product, role=ProductRoleAssignment.ProductRoles.ADMIN
    )
    
    assert product.can_manage(person1)
    assert product.can_admin(person1)
    assert not product.can_admin(person2)
