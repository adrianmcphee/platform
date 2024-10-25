from django.shortcuts import get_object_or_404

from apps.product_management.models import Product
from .base import BasePortalView


class PortalDashboardView(BasePortalView):
    """Dashboard view using PortalService"""
    template_name = "portal/dashboard.html"

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


class DashboardProductBountiesView(BasePortalView):
    """Dashboard view for product bounties"""
    template_name = "portal/dashboard/bounties.html"
    context_object_name = "bounty_claims"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_slug = self.kwargs.get("product_slug")
        product = get_object_or_404(Product, slug=product_slug)
        
        bounty_data = self.portal_service.get_product_bounties(
            product_id=product.id,
            person_id=self.request.user.person.id
        )
        
        context.update({
            "product": product,
            "bounty_claims": bounty_data.get("claims", []),
            "stats": bounty_data.get("stats", {})
        })
        return context


class DashboardProductBountyFilterView(BasePortalView):
    """Filter view for dashboard bounties"""
    template_name = "portal/dashboard/bounty_table.html"
    context_object_name = "bounties"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_slug = self.kwargs.get("product_slug")
        product = get_object_or_404(Product, slug=product_slug)
        
        filters = {}
        if query_parameter := self.request.GET.get("q"):
            for q in query_parameter.split(" "):
                key, value = q.split(":")
                if key == "sort":
                    filters["sort"] = value

        if search_query := self.request.GET.get("search-bounty"):
            filters["search"] = search_query
            
        bounty_data = self.portal_service.get_filtered_product_bounties(
            product_id=product.id,
            person_id=self.request.user.person.id,
            filters=filters
        )
        
        context.update({
            "product": product,
            "bounties": bounty_data.get("bounties", [])
        })
        return context
    
class ProductSettingView(LoginRequiredMixin, common_mixins.AttachmentMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "product_management/dashboard/product_setting.html"
    login_url = "sign_in"

    def get_success_url(self):
        return reverse("product-setting", args=(self.object.id,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = {}
        owner = self.object.get_owner()
        if isinstance(owner, Person):
            initial_make_me_owner = owner == self.request.user.person
            initial = {"make_me_owner": initial_make_me_owner}
            context["make_me_owner"] = initial_make_me_owner
        elif isinstance(owner, Organisation):
            initial = {"organisation": owner}
            context["organisation"] = owner

        context["form"] = self.form_class(instance=self.object, initial=initial)
        context["product_instance"] = self.object
        return context

    def form_valid(self, form):
        return super().form_valid(form)