from django import forms
from apps.product_management.models import Product, Bounty

class AddToCartForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    bounty = forms.ModelChoiceField(queryset=Bounty.objects.all())
