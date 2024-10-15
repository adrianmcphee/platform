from django.contrib import admin
from . import models

admin.site.register([models.Feedback])

@admin.register(models.BountyClaim)
class BountyClaimAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "bounty",
        "person",
        "expected_finish_date",
        "status",
    ]
    search_fields = [
        "bounty__title",
        "person__user__username",
        "expected_finish_date",
        "status",
    ]

@admin.register(models.BountyBid)
class BountyBidAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "bounty",
        "person",
        "amount_display",
        "expected_finish_date",
        "status",
    ]
    list_filter = ["status"]
    search_fields = [
        "bounty__title",
        "person__user__username",
        "status",
    ]

    def amount_display(self, obj):
        if obj.bounty.reward_type == 'USD':
            return f"${obj.amount_in_usd_cents / 100:.2f}" if obj.amount_in_usd_cents is not None else "N/A"
        else:
            return f"{obj.amount_in_points} Points" if obj.amount_in_points is not None else "N/A"
    amount_display.short_description = "Amount"

@admin.register(models.Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "parent"]

@admin.register(models.Expertise)
class ExpertiseAdmin(admin.ModelAdmin):
    list_display = ["pk", "name", "skill", "fa_icon", "parent"]

@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["pk", "full_name", "user"]

@admin.register(models.PersonSkill)
class PersonSkillAdmin(admin.ModelAdmin):
    list_display = ["pk", "skill", "person"]

@admin.register(models.BountyDeliveryAttempt)
class BountyDeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = ["pk", "status", "bounty_claim", "delivery_message"]
    list_filter = ["status"]

# Update the Meta classes in your models to fix pluralization
models.BountyClaim._meta.verbose_name_plural = "Bounty Claims"
models.BountyBid._meta.verbose_name_plural = "Bounty Bids"
models.Skill._meta.verbose_name_plural = "Skills"
models.Expertise._meta.verbose_name_plural = "Expertise"
models.PersonSkill._meta.verbose_name_plural = "Person Skills"
models.BountyDeliveryAttempt._meta.verbose_name_plural = "Bounty Delivery Attempts"
