from apps.product_management.services import ProductService
from apps.talent.services import BountyService
from apps.security.services import UserService
from apps.commerce.services import OrganisationService

class PortalService:
    def __init__(self):
        self.product_service = ProductService()
        self.bounty_service = BountyService()
        self.user_service = UserService()
        self.organisation_service = OrganisationService()

    def get_base_context(self, user):
        person = user.person
        return {
            "person": person,
            "photo_url": self.user_service.get_user_photo_url(person),
            "products": self.product_service.get_user_products(person)
        }

    def get_dashboard_context(self, user, product_slug, default_tab):
        person = user.person
        context = {
            "active_bounty_claims": self.bounty_service.get_active_bounty_claims(person),
            "products": self.product_service.get_products_by_user_roles(person),
            "default_tab": default_tab
        }
        if product_slug:
            context["product"] = self.product_service.get_product_by_slug(product_slug)
        return context

    def get_product_detail_context(self, product_slug, default_tab):
        product = self.product_service.get_product_by_slug(product_slug)
        challenges = self.product_service.get_product_challenges(product)
        return {
            "product": product,
            "challenges": challenges,
            "default_tab": default_tab
        }

    def get_manage_users_context(self, product_slug):
        product = self.product_service.get_product_by_slug(product_slug)
        product_users = self.product_service.get_product_users(product)
        return {
            "product": product,
            "product_users": product_users
        }

    def get_manage_bounties_context(self, product_slug):
        product = self.product_service.get_product_by_slug(product_slug)
        bounty_claims = self.bounty_service.get_product_bounty_claims(product)
        return {
            "product": product,
            "bounty_claims": bounty_claims
        }

    def get_manage_challenges_context(self, product_slug):
        product = self.product_service.get_product_by_slug(product_slug)
        challenges = self.product_service.get_product_challenges(product)
        return {
            "product": product,
            "challenges": challenges
        }

    def get_review_work_context(self):
        return {
            "bounty_deliveries": self.bounty_service.get_bounty_delivery_attempts()
        }

    def get_contributor_agreement_templates_context(self, product_slug):
        product = self.product_service.get_product_by_slug(product_slug)
        templates = self.product_service.get_contributor_agreement_templates(product)
        return {
            "product": product,
            "contributor_agreement_templates": templates
        }

    def get_product_settings_context(self, product_id):
        product = self.product_service.get_product_by_id(product_id)
        owner_type = self.product_service.get_product_owner_type(product)
        owner = self.product_service.get_product_owner(product)
        
        context = {
            "product": product,
            "owner_type": owner_type,
        }

        if owner_type == "person":
            context["make_me_owner"] = owner == product.created_by
        elif owner_type == "organisation":
            context["organisation"] = owner

        return context

    def update_product_settings(self, product_id, form_data):
        return self.product_service.update_product(product_id, form_data)

    def filter_product_challenges(self, product_slug, filter_params):
        product = self.product_service.get_product_by_slug(product_slug)
        return self.product_service.filter_challenges(product, filter_params)

    def filter_product_bounties(self, product_slug, filter_params):
        product = self.product_service.get_product_by_slug(product_slug)
        return self.bounty_service.filter_bounties(product, filter_params)

