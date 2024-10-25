from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from apps.common.mixins import PersonSearchMixin
from apps.security.models import ProductRoleAssignment
from apps.security.forms import ProductRoleAssignmentForm
from apps.product_management.models import Product
from .base import BasePortalView


class ManageUsersView(BasePortalView):
    """User management view using PortalService"""
    template_name = "portal/user/manage_users.html"

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
    template_name = "portal/user/add_user.html"

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
        return reverse("portal:manage-users", args=(self.kwargs.get("product_slug"),))