from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

from apps.product_management.services import ProductService
from apps.talent.services import BountyService
from apps.security.services import UserService
from apps.commerce.services import OrganisationService
from .services import PortalService

class PortalBaseView(LoginRequiredMixin):
    login_url = "sign_in"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal_service = PortalService()
        context.update(portal_service.get_base_context(self.request.user))
        return context

class DashboardView(PortalBaseView, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal_service = PortalService()
        context.update(portal_service.get_dashboard_context(
            self.request.user,
            self.kwargs.get("product_slug", ""),
            self.kwargs.get("default_tab", 0)
        ))
        return context

class ManageBountiesView(PortalBaseView, TemplateView):
    template_name = "portal/my_bounties.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bounty_service = BountyService()
        context.update(bounty_service.get_user_bounties_context(self.request.user.person))
        return context

class ManageUsersView(PortalBaseView, TemplateView):
    template_name = "portal/manage_users.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_service = ProductService()
        context.update(product_service.get_product_users_context(self.kwargs.get("product_slug")))
        return context

class AddProductUserView(PortalBaseView, CreateView):
    template_name = "portal/add_product_user.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_service = ProductService()
        context.update(product_service.get_add_product_user_context(self.kwargs.get("product_slug")))
        return context

    def post(self, request, *args, **kwargs):
        product_service = ProductService()
        result = product_service.add_product_user(request.POST, self.kwargs.get("product_slug"))
        if result['success']:
            messages.success(request, "The user was successfully added!")
            return redirect(reverse("manage-users", args=(result['product_slug'],)))
        return super().post(request, *args, **kwargs)

class UpdateProductUserView(PortalBaseView, UpdateView):
    template_name = "portal/update_product_user.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_service = ProductService()
        context.update(product_service.get_update_product_user_context(
            self.kwargs.get("product_slug"),
            self.kwargs.get("pk")
        ))
        return context

    def post(self, request, *args, **kwargs):
        product_service = ProductService()
        result = product_service.update_product_user(
            request.POST,
            self.kwargs.get("product_slug"),
            self.kwargs.get("pk")
        )
        if result['success']:
            return redirect(reverse("manage-users", args=(result['product_slug'],)))
        return super().post(request, *args, **kwargs)

class ProductSettingView(PortalBaseView, UpdateView):
    template_name = "portal/product_setting.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_service = ProductService()
        context.update(product_service.get_product_setting_context(self.kwargs.get("pk")))
        return context

    def form_valid(self, form):
        product_service = ProductService()
        return product_service.update_product_settings(form)

class PortalBountyClaimRequestsView(PortalBaseView, ListView):
    template_name = "portal/bounty_claim_requests.html"

    def get_queryset(self):
        bounty_service = BountyService()
        return bounty_service.get_user_bounty_claims(self.request.user.person)

class PortalProductDetailView(PortalBaseView, DetailView):
    template_name = "portal/product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal_service = PortalService()
        context.update(portal_service.get_product_detail_context(
            self.kwargs.get("product_slug"),
            self.kwargs.get("default_tab", 0)
        ))
        return context

class PortalProductChallengesView(PortalBaseView, ListView):
    template_name = "portal/manage_challenges.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_service = ProductService()
        context.update(product_service.get_product_challenges_context(self.kwargs.get("product_slug")))
        return context

    def get_queryset(self):
        product_service = ProductService()
        return product_service.get_product_challenges(self.kwargs.get("product_slug"))

class PortalProductChallengeFilterView(PortalBaseView, TemplateView):
    template_name = "portal/challenge_table.html"

    def get(self, request, *args, **kwargs):
        product_service = ProductService()
        context = product_service.filter_product_challenges(
            self.kwargs.get("product_slug"),
            request.GET
        )
        return self.render_to_response(context)

class PortalProductBountiesView(PortalBaseView, ListView):
    template_name = "portal/manage_bounties.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bounty_service = BountyService()
        context.update(bounty_service.get_product_bounties_context(self.kwargs.get("product_slug")))
        return context

    def get_queryset(self):
        bounty_service = BountyService()
        return bounty_service.get_product_bounty_claims(self.kwargs.get("product_slug"))

class PortalProductBountyFilterView(PortalBaseView, TemplateView):
    template_name = "portal/bounty_table.html"

    def get(self, request, *args, **kwargs):
        bounty_service = BountyService()
        context = bounty_service.filter_product_bounties(
            self.kwargs.get("product_slug"),
            request.GET
        )
        return self.render_to_response(context)

class PortalReviewWorkView(PortalBaseView, ListView):
    template_name = "portal/review_work.html"

    def get_queryset(self):
        bounty_service = BountyService()
        return bounty_service.get_bounty_delivery_attempts()

class PortalContributorAgreementTemplateListView(PortalBaseView, ListView):
    template_name = "portal/contributor_agreement_templates.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_service = ProductService()
        context.update(product_service.get_contributor_agreement_templates_context(self.kwargs.get("product_slug")))
        return context

    def get_queryset(self):
        product_service = ProductService()
        return product_service.get_contributor_agreement_templates(self.kwargs.get("product_slug"))

def bounty_claim_actions(request, pk):
    bounty_service = BountyService()
    result = bounty_service.process_bounty_claim_action(pk, request.GET.get("action"))
    return redirect(reverse("portal-product-bounties", args=(result['product_slug'],)))
