from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from apps.security.models import ProductRoleAssignment

from ..models import Product, Challenge, ProductContributorAgreementTemplate
from ..forms import ProductRoleAssignmentForm, ContributorAgreementTemplateForm
from apps.common.mixins import PersonSearchMixin

class BasePortalView(LoginRequiredMixin):
    """Base class for portal views with service initialization"""
    login_url = "sign_in"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Service instances will be initialized in dispatch
        self.portal_service = None
        self.product_service = None
        self.challenge_service = None

    def dispatch(self, request, *args, **kwargs):
        # Initialize services
        from ..services import (
            PortalService, 
            ProductManagementService,
            ChallengeService,
            BountyService,
            ProductSupportService
        )
        
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

class PortalDashboardView(BasePortalView, TemplateView):
    """Dashboard view using PortalService"""
    template_name = "product_management/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = context["person"]

        # Get dashboard data for specific product if specified
        if product_slug := self.kwargs.get("product_slug"):
            product = get_object_or_404(Product, slug=product_slug)
            product_dashboard = self.portal_service.get_product_dashboard(
                product_id=product.id,
                person_id=person.id
            )
            context["product_dashboard"] = product_dashboard
            context["product"] = product

        context["default_tab"] = self.kwargs.get("default_tab", 0)
        return context

class ManageBountiesView(BasePortalView, TemplateView):
    """Bounty management view using PortalService"""
    template_name = "product_management/portal/my_bounties.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.request.user.person
        
        bounty_data = self.portal_service.get_bounty_management(
            person_id=person.id,
            filters=self.request.GET.dict()
        )
        context.update({"bounty_data": bounty_data})
        return context

class ManageUsersView(BasePortalView, TemplateView):
    """User management view using PortalService"""
    template_name = "product_management/portal/manage_users.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.request.user.person
        product_slug = self.kwargs.get("product_slug")
        product = get_object_or_404(Product, slug=product_slug)
        
        user_data = self.portal_service.get_user_management(
            product_id=product.id,
            person_id=person.id
        )
        
        if not user_data:
            raise PermissionDenied("No permission to manage users")
            
        context.update({
            "product": product,
            "user_data": user_data
        })
        return context

class AddProductUserView(BasePortalView, PersonSearchMixin, CreateView):
    """Add user view with service integration"""
    model = ProductRoleAssignment
    form_class = ProductRoleAssignmentForm
    template_name = "product_management/portal/add_product_user.html"

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        if product_slug := self.kwargs.get("product_slug"):
            kwargs["initial"] = {"product": get_object_or_404(Product, slug=product_slug)}
        return kwargs

    def form_valid(self, form):
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        form.instance.product = product
        
        # Verify permission using service
        if not self.portal_service._can_manage_users(
            product_id=product.id,
            person_id=self.request.user.person.id
        ):
            raise PermissionDenied("No permission to add users")
            
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("manage-users", args=(self.kwargs.get("product_slug"),))

class ReviewWorkView(BasePortalView, TemplateView):
    """Work review view using PortalService"""
    template_name = "product_management/portal/review_work.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.request.user.person
        product_slug = self.kwargs.get("product_slug")
        product = get_object_or_404(Product, slug=product_slug)
        
        review_data = self.portal_service.get_work_review_queue(
            product_id=product.id,
            reviewer_id=person.id
        )
        
        if not review_data:
            raise PermissionDenied("No permission to review work")
            
        context.update({
            "product": product,
            "review_data": review_data
        })
        return context

class ContributorAgreementView(BasePortalView, DetailView):
    """Contributor agreement view using ProductSupportService"""
    model = ProductContributorAgreementTemplate
    template_name = "product_management/portal/contributor_agreement_template_detail.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        person = self.request.user.person
        
        # Get agreement status from service
        agreement_data = self.portal_service.get_contribution_overview(person.id)
        
        context.update({
            "product": product,
            "agreement_data": agreement_data
        })
        return context

    def post(self, request, *args, **kwargs):
        """Handle agreement acceptance"""
        template = self.get_object()
        person = request.user.person
        
        success, message = self.portal_service.product_support_service.manage_contributor_agreement(
            product_id=template.product.id,
            person_id=person.id,
            agreement_id=template.id,
            action="accept"
        )
        
        if request.htmx:
            if success:
                return JsonResponse({"redirect": self.get_success_url()})
            return JsonResponse({"error": message}, status=400)
            
        return redirect(self.get_success_url())

# Additional views can be similarly refactored...