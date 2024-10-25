from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.product_management.services import (
    PortalService, 
    ProductManagementService,
    ChallengeService,
    BountyService,
    ProductSupportService
)

class BasePortalView(LoginRequiredMixin):
    """Base class for portal views with service initialization"""
    login_url = "sign_in"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.portal_service = None
        self.product_service = None
        self.challenge_service = None

    def dispatch(self, request, *args, **kwargs):
        self.portal_service = PortalService(
            product_service=ProductManagementService(),
            challenge_service=ChallengeService(),
            bounty_service=BountyService(),
            product_support_service=ProductSupportService()
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.request.user.person
        dashboard_data = self.portal_service.get_user_dashboard(person.id)
        context.update({
            "person": person,
            "photo_url": person.get_photo_url(),
            "dashboard_data": dashboard_data
        })
        return context