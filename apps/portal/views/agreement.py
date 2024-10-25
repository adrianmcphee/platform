from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView
from django.http import JsonResponse

from apps.product_management.models import (
    Product,
    ProductContributorAgreementTemplate
)
from .base import BasePortalView


class ContributorAgreementView(BasePortalView, DetailView):
    """Contributor agreement view using ProductSupportService"""
    model = ProductContributorAgreementTemplate
    template_name = "portal/agreement/detail.html"
    
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

    def get_success_url(self):
        return reverse("portal:contributor-agreement", args=[
            self.kwargs.get("product_slug"),
            self.object.id
        ])


class ContributorAgreementListView(BasePortalView):
    """List view for contributor agreements"""
    template_name = "portal/agreement/list.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        person = self.request.user.person

        agreements_data = self.portal_service.product_support_service.get_product_agreements(
            product_id=product.id,
            person_id=person.id
        )
        
        context.update({
            "product": product,
            "agreements_data": agreements_data
        })
        return context


class CreateContributorAgreementView(BasePortalView):
    """Create new contributor agreement"""
    template_name = "portal/agreement/create.html"
    model = ProductContributorAgreementTemplate
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        
        if not self.portal_service._can_manage_agreements(
            product_id=product.id,
            person_id=self.request.user.person.id
        ):
            raise PermissionDenied("No permission to create agreements")
            
        context["product"] = product
        return context

    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        success, message, agreement_id = self.portal_service.product_support_service.create_agreement(
            product_id=product.id,
            creator_id=request.user.person.id,
            title=request.POST.get("title"),
            content=request.POST.get("content"),
            effective_date=request.POST.get("effective_date")
        )

        if request.htmx:
            if success:
                return JsonResponse({"redirect": self.get_success_url(agreement_id)})
            return JsonResponse({"error": message}, status=400)

        if success:
            return redirect(self.get_success_url(agreement_id))
        return self.render_to_response(self.get_context_data(error=message))

    def get_success_url(self, agreement_id):
        return reverse("portal:contributor-agreement", args=[
            self.kwargs.get("product_slug"),
            agreement_id
        ])