from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from apps.product_management.models import Product
from .base import BasePortalView


class ManageBountiesView(BasePortalView):
    """Bounty management view using PortalService"""
    template_name = "portal/bounty/my_bounties.html"  # Updated template path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.request.user.person
        
        bounty_data = self.portal_service.get_bounty_management(
            person_id=person.id,
            filters=self.request.GET.dict()
        )
        context.update({"bounty_data": bounty_data})
        return context


class ReviewWorkView(BasePortalView):
    """Work review view using PortalService"""
    template_name = "portal/bounty/review_work.html"  # Updated template path

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
