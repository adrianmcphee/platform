from django.contrib import admin

from apps.product_management import models as product
from apps.commerce.models import Organisation
from apps.talent.models import Person
from .models import ProductTree, ProductArea

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

import json
from django.core.serializers.json import DjangoJSONEncoder

from django.utils.safestring import mark_safe

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.db import connection
from django.db import transaction

@admin.register(product.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "person", "organisation", "owner_type", "is_private"]
    list_filter = ["is_private"]
    search_fields = ["slug", "name", "person__user__username", "organisation__name"]
    raw_id_fields = ["person", "organisation"]
    filter_horizontal = ("attachments",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('person', 'organisation')

    def owner_type(self, obj):
        owner = obj.get_owner()
        if isinstance(owner, Organisation):
            return "Organisation"
        elif isinstance(owner, Person):
            return "Person"
        else:
            return "Unknown"
    owner_type.short_description = "Owner Type"

class OwnerTypeFilter(admin.SimpleListFilter):
    title = 'Owner Type'
    parameter_name = 'owner_type'

    def lookups(self, request, model_admin):
        return (
            ('person', 'Person'),
            ('organisation', 'Organisation'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'person':
            return queryset.filter(organisation__isnull=True, person__isnull=False)
        if self.value() == 'organisation':
            return queryset.filter(organisation__isnull=False)

ProductAdmin.list_filter += (OwnerTypeFilter,)

@admin.register(product.Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "status"]
    list_filter = ["status"]
    search_fields = ["name", "product__name"]


@admin.register(ProductTree)
class ProductTreeAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "created_at"]
    search_fields = ["name", "product__name"]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        product_tree = self.get_object(request, object_id)
        extra_context['product_areas'] = ProductArea.get_root_nodes().filter(product_tree=product_tree)
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

@admin.register(ProductArea)
class ProductAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_tree', 'path')
    search_fields = ('name', 'product_tree__name')
    raw_id_fields = ('parent', 'product_tree')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not qs.filter(parent__isnull=True).exists():
            with transaction.atomic():
                ProductArea.objects.create(name="Root", product_tree=None)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = ProductArea.objects.exclude(id=request.resolver_match.kwargs.get('object_id'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # New object
            parent = form.cleaned_data.get('parent')
            if parent:
                obj.path = f"{parent.path}/{obj.id}"
            else:
                obj.path = obj.id
        super().save_model(request, obj, form, change)

    def move_node(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select a single node to move.", level='error')
            return

        node = queryset.first()
        parent_id = request.POST.get('parent')
        if parent_id:
            parent = ProductArea.objects.get(id=parent_id)
            node.move(parent)
            self.message_user(request, f"Moved {node.name} under {parent.name}")
        else:
            self.message_user(request, "No parent selected for move operation.", level='error')

    move_node.short_description = "Move selected node"
    actions = [move_node]

    class Media:
        js = ('admin/js/product_area_admin.js',)  # You'll need to create this JS file

@admin.register(product.Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "initiative", "status", "priority", "featured"]
    list_filter = ["status", "priority", "featured"]
    search_fields = ["title", "product__name", "initiative__name"]
    filter_horizontal = ["attachments"]

@admin.register(product.Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "status", "entry_deadline", "judging_deadline"]
    list_filter = ["status"]
    search_fields = ["title", "product__name"]
    filter_horizontal = ["attachments"]

class BountySkillInline(admin.TabularInline):
    model = product.BountySkill
    extra = 1
    filter_horizontal = ('expertise',)

@admin.register(product.Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "challenge", "competition", "status", "reward_type", "reward_display"]
    list_filter = ["status", "reward_type"]
    search_fields = ["title", "product__name", "challenge__title", "competition__title"]
    filter_horizontal = ["attachments"]
    inlines = [BountySkillInline]

    def reward_display(self, obj):
        if obj.reward_type == 'USD':
            return f"${obj.reward_in_usd_cents / 100:.2f}"
        else:
            return f"{obj.reward_in_points} Points"
    reward_display.short_description = "Reward"

@admin.register(product.BountySkill)
class BountySkillAdmin(admin.ModelAdmin):
    list_display = ["bounty", "skill", "expertise_list"]
    search_fields = ["bounty__title", "skill__name"]
    filter_horizontal = ["expertise"]

    def expertise_list(self, obj):
        return ", ".join([e.name for e in obj.expertise.all()])
    expertise_list.short_description = "Expertises"

@admin.register(product.CompetitionEntry)
class CompetitionEntryAdmin(admin.ModelAdmin):
    list_display = ["competition", "submitter", "status", "entry_time"]
    list_filter = ["status"]
    search_fields = ["competition__title", "submitter__user__username"]

@admin.register(product.CompetitionEntryRating)
class CompetitionEntryRatingAdmin(admin.ModelAdmin):
    list_display = ["entry", "rater", "rating"]
    list_filter = ["rating"]
    search_fields = ["entry__bounty__title", "rater__user__username"]

@admin.register(product.ChallengeDependency)
class ChallengeDependencyAdmin(admin.ModelAdmin):
    list_display = ["preceding_challenge", "subsequent_challenge"]
    search_fields = ["preceding_challenge__title", "subsequent_challenge__title"]

@admin.register(product.ContributorGuide)
class ContributorGuideAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "skill"]
    search_fields = ["title", "product__name", "skill__name"]

@admin.register(product.Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "person"]
    search_fields = ["title", "product__name", "person__user__username"]

@admin.register(product.Bug)
class BugAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "person"]
    search_fields = ["title", "product__name", "person__user__username"]

@admin.register(product.ProductContributorAgreementTemplate)
class ProductContributorAgreementTemplateAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "effective_date"]
    search_fields = ["title", "product__name"]

@admin.register(product.IdeaVote)
class IdeaVoteAdmin(admin.ModelAdmin):
    list_display = ["voter", "idea"]
    search_fields = ["voter__username", "idea__title"]

@admin.register(product.ProductContributorAgreement)
class ProductContributorAgreementAdmin(admin.ModelAdmin):
    list_display = ["agreement_template", "person", "accepted_at"]
    search_fields = ["agreement_template__title", "person__user__username"]

# Fix pluralization issues
product.Bounty._meta.verbose_name_plural = "Bounties"
product.BountySkill._meta.verbose_name_plural = "Bounty Skills"
product.ChallengeDependency._meta.verbose_name_plural = "Challenge dependencies"
product.CompetitionEntry._meta.verbose_name_plural = "Competition entries"
