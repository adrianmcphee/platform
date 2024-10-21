from django.test import TestCase
from apps.product_management.models import Product
from apps.security.models import ProductRoleAssignment, OrganisationPersonRoleAssignment
from apps.talent.models import Person
from apps.commerce.models import Organisation

class ProductAccessTestCase(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Test Org")
        self.product = Product.objects.create(name="Test Product", organisation=self.org)
        self.person1 = Person.objects.create(name="Person 1")
        self.person2 = Person.objects.create(name="Person 2")
        self.person3 = Person.objects.create(name="Person 3")

        OrganisationPersonRoleAssignment.objects.create(
            person=self.person1, organisation=self.org, role=OrganisationPersonRoleAssignment.OrganisationRoles.MEMBER
        )
        ProductRoleAssignment.objects.create(
            person=self.person2, product=self.product, role=ProductRoleAssignment.ProductRoles.MEMBER
        )

    def test_global_visibility(self):
        self.product.visibility = Product.Visibility.GLOBAL
        self.product.save()
        
        self.assertTrue(self.product.is_visible_to(self.person1))
        self.assertTrue(self.product.is_visible_to(self.person2))
        self.assertTrue(self.product.is_visible_to(self.person3))

    def test_org_only_visibility(self):
        self.product.visibility = Product.Visibility.ORG_ONLY
        self.product.save()
        
        self.assertTrue(self.product.is_visible_to(self.person1))
        self.assertFalse(self.product.is_visible_to(self.person2))
        self.assertFalse(self.product.is_visible_to(self.person3))

    def test_restricted_visibility(self):
        self.product.visibility = Product.Visibility.RESTRICTED
        self.product.save()
        
        self.assertFalse(self.product.is_visible_to(self.person1))
        self.assertTrue(self.product.is_visible_to(self.person2))
        self.assertFalse(self.product.is_visible_to(self.person3))

    def test_manager_permissions(self):
        ProductRoleAssignment.objects.create(
            person=self.person1, product=self.product, role=ProductRoleAssignment.ProductRoles.MANAGER
        )
        
        self.assertTrue(self.product.can_manage(self.person1))
        self.assertFalse(self.product.can_manage(self.person2))
        self.assertFalse(self.product.can_admin(self.person1))

    def test_admin_permissions(self):
        ProductRoleAssignment.objects.create(
            person=self.person1, product=self.product, role=ProductRoleAssignment.ProductRoles.ADMIN
        )
        
        self.assertTrue(self.product.can_manage(self.person1))
        self.assertTrue(self.product.can_admin(self.person1))
        self.assertFalse(self.product.can_admin(self.person2))

