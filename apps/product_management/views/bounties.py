from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages

from ..models import Challenge, Product
from ..forms import BountyForm
from .. import utils
from apps.talent.utils import serialize_skills
from apps.talent.models import Skill, Expertise
from apps.talent.forms import PersonSkillFormSet
from ..services.bounty_service import BountyService

bounty_service = BountyService()

class BountyListView(ListView):
    context_object_name = "bounties"
    template_name = "product_management/bounty/list.html"
    paginate_by = 51

    def get_template_names(self):
        if self.request.htmx:
            return ["product_management/bounty/partials/list_partials.html"]
        return ["product_management/bounty/list.html"]

    def get_queryset(self):
        filters = {}
        if expertise := self.request.GET.get("expertise"):
            filters["expertise"] = expertise
        if status := self.request.GET.get("status"):
            filters["status"] = status
        if skill := self.request.GET.get("skill"):
            filters["skill"] = skill
        
        bounties, _ = bounty_service.get_bounties(filters=filters, page=self.request.GET.get('page', 1), per_page=self.paginate_by)
        return bounties

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["BountyStatus"] = bounty_service.get_bounty_statuses()
        
        expertises = []
        if skill := self.request.GET.get("skill"):
            expertises = Expertise.get_roots().filter(skill=skill)

        context["skills"] = [serialize_skills(skill) for skill in Skill.get_roots()]
        context["expertises"] = [utils.serialize_other_type_tree(expertise) for expertise in expertises]
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx and self.request.GET.get("target") == "skill":
            list_html = render(
                self.request,
                "product_management/bounty/partials/list_partials.html",
                context,
            ).content.decode('utf-8')
            expertise_html = render(
                self.request,
                "product_management/bounty/partials/expertise.html",
                context,
            ).content.decode('utf-8')

            return JsonResponse(
                {
                    "list_html": list_html,
                    "expertise_html": expertise_html,
                    "item_found_count": len(context["object_list"]),
                }
            )
        return super().render_to_response(context, **response_kwargs)

class ProductBountyListView(utils.BaseProductDetailView, ListView):
    context_object_name = "bounties"
    template_name = "product_management/product_bounties.html"

    def get_queryset(self):
        product = self.get_context_data().get("product")
        return bounty_service.get_product_bounties(product.id)

class BountyDetailView(utils.BaseProductDetailView, DetailView):
    template_name = "product_management/bounty_detail.html"

    def get_object(self):
        return bounty_service.get_bounty_details(self.kwargs.get('pk'), self.request.user.id if self.request.user.is_authenticated else None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bounty = self.object
        
        context.update({
            "product": bounty['challenge']['product'],
            "challenge": bounty['challenge'],
            "claimed_by": bounty.get('claimed_by'),
            "show_actions": bounty.get('can_be_claimed', False) or bounty.get('can_be_modified', False) or bounty.get('created_bounty_claim_request', False),
            "can_be_claimed": bounty.get('can_be_claimed', False),
            "can_be_modified": bounty.get('can_be_modified', False),
            "is_product_admin": bounty.get('can_be_modified', False),
            "created_bounty_claim_request": bounty.get('created_bounty_claim_request', False),
            "bounty_claim": bounty.get('bounty_claim'),
        })

        return context

class CreateBountyView(LoginRequiredMixin, utils.BaseProductDetailView, CreateView):
    form_class = BountyForm
    template_name = "product_management/create_bounty.html"

    def get_success_url(self):
        return reverse("challenge_detail", args=(self.object['challenge']['product']['slug'], self.object['challenge']['id']))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = Challenge.objects.get(pk=self.kwargs.get("challenge_id"))
        context["skills"] = [serialize_skills(skill) for skill in Skill.get_roots()]
        context["empty_form"] = PersonSkillFormSet().empty_form
        return context

    def form_valid(self, form):
        challenge_id = self.kwargs.get("challenge_id")
        success, message, bounty_id = bounty_service.create_bounty(challenge_id, form.cleaned_data, self.request.user.id)
        if success:
            self.object = bounty_service.get_bounty_details(bounty_id)
            return HttpResponseRedirect(self.get_success_url())
        else:
            form.add_error(None, message)
            return self.form_invalid(form)

class UpdateBountyView(LoginRequiredMixin, utils.BaseProductDetailView, UpdateView):
    form_class = BountyForm
    template_name = "product_management/update_bounty.html"

    def get_object(self):
        return bounty_service.get_bounty_details(self.kwargs.get('pk'))

    def get_success_url(self):
        return reverse("challenge_detail", args=(self.object['challenge']['product']['slug'], self.object['challenge']['id']))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.object['challenge']
        context["skills"] = [serialize_skills(skill) for skill in Skill.get_roots()]
        context["empty_form"] = PersonSkillFormSet().empty_form
        return context

    def form_valid(self, form):
        success, message = bounty_service.update_bounty_status(self.kwargs.get('pk'), form.cleaned_data, self.request.user.id)
        if success:
            self.object = bounty_service.get_bounty_details(self.kwargs.get('pk'))
            return HttpResponseRedirect(self.get_success_url())
        else:
            form.add_error(None, message)
            return self.form_invalid(form)

class DeleteBountyView(LoginRequiredMixin, DeleteView):
    def get_success_url(self):
        return reverse("challenge_detail", args=(self.object['challenge']['product']['slug'], self.object['challenge']['id']))

    def delete(self, request, *args, **kwargs):
        success, message = bounty_service.delete_bounty(self.kwargs.get('pk'), request.user.id)
        if success:
            messages.success(request, "The bounty has been successfully deleted.")
        else:
            messages.error(request, message)
        return HttpResponseRedirect(self.get_success_url())

def bounty_claim_actions(request, pk):
    action_type = request.GET.get("action")
    success, message = bounty_service.process_claim(pk, request.user.id, action_type)
    if success:
        return redirect(reverse("dashboard-product-bounties", args=(message,)))
    else:
        return JsonResponse({"error": message}, status=400)

class DeleteBountyClaimView(LoginRequiredMixin, DeleteView):
    success_url = reverse_lazy("dashboard-bounty-requests")

    def delete(self, request, *args, **kwargs):
        success, message = bounty_service.delete_bounty_claim(self.kwargs.get('pk'), request.user.id)
        if success:
            messages.success(request, "The bounty claim has been successfully cancelled.")
        else:
            messages.error(request, message)

        if request.htmx:
            bounty = bounty_service.get_bounty_details(message)
            return render(
                request,
                "product_management/partials/buttons/create_bounty_claim_button.html",
                {"bounty": bounty},
            )

        return HttpResponseRedirect(self.get_success_url())
