from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Sum, Case, When, Value, IntegerField

from ..models import Product, Initiative
from ..forms import ChallengeForm
from .. import utils
from apps.talent.forms import PersonSkillFormSet
from apps.talent.models import BountyClaim
from apps.security.models import ProductRoleAssignment
from ..services.challenge_service import ChallengeService

challenge_service = ChallengeService()

class ChallengeListView(ListView):
    context_object_name = "challenges"
    template_name = "product_management/challenges.html"
    paginate_by = 10

    def get_queryset(self):
        filters = {'statuses': ['ACTIVE', 'BLOCKED', 'COMPLETED']}  # Exclude DRAFT status
        return challenge_service.get_filtered_challenges(self.kwargs.get('product_slug'), filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge_status"] = challenge_service.get_challenge_statuses()
        return context

class ProductChallengesView(utils.BaseProductDetailView, ListView):
    template_name = "product_management/product_challenges.html"
    context_object_name = "challenges"

    def get_queryset(self):
        product = self.get_context_data()["product"]
        return challenge_service.get_filtered_challenges(product.id, {})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge_status"] = challenge_service.get_challenge_statuses()
        return context

class ChallengeDetailView(utils.BaseProductDetailView, DetailView):
    context_object_name = "challenge"
    template_name = "product_management/challenge_detail.html"

    def get_object(self):
        return challenge_service.get_challenge_details(self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        challenge = self.object
        user = self.request.user

        context["BountyStatus"] = challenge_service.get_bounty_statuses()
        context["bounties"] = challenge_service.get_challenge_bounties(challenge['id'])
        context["total_reward"] = challenge_service.calculate_rewards(challenge['id'])
        context["does_have_permission"] = challenge_service.check_challenge_permission(challenge['id'], user.id)

        if user.is_authenticated:
            person = user.person
            context["agreement_status"] = challenge_service.check_contributor_agreement(challenge['product']['id'], person.id)
            context["agreement_template"] = challenge_service.get_contributor_agreement_template(challenge['product']['id'])

        return context

class CreateChallengeView(LoginRequiredMixin, utils.BaseProductDetailView, CreateView):
    form_class = ChallengeForm
    template_name = "product_management/create_challenge.html"
    login_url = "sign_in"

    def get_success_url(self):
        return reverse("challenge_detail", args=(self.object['product']['slug'], self.object['id']))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        context["product"] = product
        context["empty_form"] = PersonSkillFormSet().empty_form
        return context

    def form_valid(self, form):
        product = get_object_or_404(Product, slug=self.kwargs.get("product_slug"))
        success, message, challenge_id = challenge_service.create_challenge(
            product.id,
            form.cleaned_data['title'],
            form.cleaned_data['description'],
            form.cleaned_data.get('initiative'),
            self.request.user.id,
            form.cleaned_data
        )
        if success:
            self.object = challenge_service.get_challenge_details(challenge_id)
            return HttpResponseRedirect(self.get_success_url())
        else:
            form.add_error(None, message)
            return self.form_invalid(form)

class UpdateChallengeView(LoginRequiredMixin, utils.BaseProductDetailView, UpdateView):
    form_class = ChallengeForm
    template_name = "product_management/update_challenge.html"
    login_url = "sign_in"

    def get_object(self):
        return challenge_service.get_challenge_details(self.kwargs.get('pk'))

    def get_success_url(self):
        return reverse("challenge_detail", args=(self.object['product']['slug'], self.object['id']))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.object['product']
        return context

    def form_valid(self, form):
        success, message = challenge_service.update_challenge(self.kwargs.get('pk'), form.cleaned_data, self.request.user.id)
        if success:
            self.object = challenge_service.get_challenge_details(self.kwargs.get('pk'))
            return HttpResponseRedirect(self.get_success_url())
        else:
            form.add_error(None, message)
            return self.form_invalid(form)

class DeleteChallengeView(LoginRequiredMixin, DeleteView):
    template_name = "product_management/delete_challenge.html"
    login_url = "sign_in"

    def get_object(self):
        return challenge_service.get_challenge_details(self.kwargs.get('pk'))

    def get_success_url(self):
        return reverse("product_challenges", args=[self.object['product']['slug']])

    def dispatch(self, request, *args, **kwargs):
        challenge = self.get_object()
        person = request.user.person
        if challenge_service.can_delete_challenge(challenge['id'], person.id):
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, "You do not have rights to remove this challenge.")
        return redirect("challenge_detail", product_slug=challenge['product']['slug'], pk=challenge['id'])

    def delete(self, request, *args, **kwargs):
        success, message = challenge_service.delete_challenge(self.get_object()['id'], request.user.id)
        if success:
            messages.success(request, "The challenge has been successfully deleted!")
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.error(request, message)
            return self.get(request, *args, **kwargs)

def redirect_challenge_to_bounties(request):
    return redirect(reverse("bounties"))
