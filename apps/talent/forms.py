from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.talent import models as talent

from .models import BountyClaim, BountyDeliveryAttempt, Feedback, Person, PersonSkill, Skill, Expertise


def _get_text_input_class():
    return (
        "pt-2 px-4 pb-3 w-full text-sm text-black border border-solid border-[#D9D9D9] focus:outline-none rounded-sm"
    )


def _get_text_area_class():
    return (
        "pt-2 px-4 pb-3 min-h-[104px] w-full text-sm text-black border border-solid border-[#D9D9D9]"
        " focus:outline-none rounded-sm"
    )


def _get_text_input_class_for_link():
    return (
        "block w-full h-full max-w-full rounded-r-sm shadow-none border border-solid border-[#D9D9D9] py-1.5 px-3"
        " text-gray-900 text-sm ring-0 placeholder:text-gray-400 focus:ring-0 focus-visible:outline-none sm:text-sm"
        " sm:leading-6 h-9"
    )


def _get_choice_box_class():
    return "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"


class PersonProfileForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            'full_name', 'preferred_name', 'photo', 'headline', 'overview',
            'location', 'send_me_bounties', 'current_position',
            'twitter_link', 'linkedin_link', 'github_link', 'website_link'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'headline': forms.TextInput(attrs={'class': 'form-control'}),
            'overview': forms.Textarea(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'current_position': forms.TextInput(attrs={'class': 'form-control'}),
            'twitter_link': forms.URLInput(attrs={'class': 'form-control'}),
            'linkedin_link': forms.URLInput(attrs={'class': 'form-control'}),
            'github_link': forms.URLInput(attrs={'class': 'form-control'}),
            'website_link': forms.URLInput(attrs={'class': 'form-control'}),
            'send_me_bounties': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['send_me_bounties'].help_text = 'Get notified when a new bounty is added.'


class PersonSkillForm(forms.ModelForm):
    class Meta:
        model = PersonSkill
        fields = ['person', 'skill']
        widgets = {
            'person': forms.Select(attrs={'class': 'form-control'}),
            'skill': forms.Select(attrs={'class': 'form-control'}),
        }

    expertise = forms.ModelMultipleChoiceField(
        queryset=Expertise.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['expertise'].initial = self.instance.expertise.all()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
        return instance

PersonSkillFormSet = forms.inlineformset_factory(
    Person, PersonSkill, form=PersonSkillForm,
    extra=1, can_delete=True
)


class FeedbackForm(forms.ModelForm):
    stars = forms.CharField(
        widget=forms.HiddenInput(
            attrs={
                "id": "star-rating",
                "name": "star-rating",
                "display": "none",
            }
        )
    )

    class Meta:
        model = Feedback
        fields = ["message", "stars"]

        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": _get_text_area_class(),
                    "placeholder": "Write your feedback here",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        stars = self.data.get("stars", None)
        try:
            star_rating = int(stars.split("-")[-1])
            cleaned_data["stars"] = star_rating
        except (AttributeError, ValueError):
            raise ValidationError(
                _("Something went wrong. The given star value should be in 'star-x' format where x is an integer.")
            )
        return cleaned_data


class BountyDeliveryAttemptForm(forms.ModelForm):
    # bounty_claim = forms.ModelChoiceField(
    #     empty_label="Select a Bounty Claim",
    #     queryset=BountyClaim.objects.filter(status=BountyClaim.Status.IN_PROGRESS),
    #     label="Bounty Claim",
    #     widget=forms.Select(
    #         attrs={
    #             "class": (
    #                 "mt-2 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset"
    #                 " ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
    #             ),
    #         }
    #     ),
    # )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.request:
            pk = self.request.GET.get("id", None)
            queryset = BountyClaim.objects.filter(id=pk)
            self.fields["bounty_claim"].queryset = queryset
            self.fields["bounty_claim"].initial = queryset.first()
            self.fields["bounty_claim"].empty_label = None

    class Meta:
        model = BountyDeliveryAttempt
        fields = [
            "bounty_claim",
            "delivery_message",
        ]

        widgets = {
            "delivery_message": forms.Textarea(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 p-2 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300"
                        " placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm"
                        " sm:leading-6"
                    ),
                }
            ),
        }
