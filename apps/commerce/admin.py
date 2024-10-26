from django.contrib import admin
from .models import (
    Organisation,
    OrganisationWallet,
    OrganisationWalletTransaction,
    OrganisationPointAccount,
    ProductPointAccount,
    PointTransaction,
    OrganisationPointGrant,
    PlatformFeeConfiguration,
    Cart,
    CartLineItem,
    SalesOrder,
    SalesOrderLineItem,
    PointOrder,
)

@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "tax_id")
    search_fields = ("name", "tax_id")
    list_filter = ("country",)

class OrganisationWalletTransactionInline(admin.TabularInline):
    model = OrganisationWalletTransaction
    extra = 0
    readonly_fields = ("created_at", "transaction_type", "amount_usd", "description")

    def amount_usd(self, obj):
        return f"${obj.amount_cents / 100:.2f}"
    amount_usd.short_description = "Amount (USD)"

@admin.register(OrganisationWallet)
class OrganisationWalletAdmin(admin.ModelAdmin):
    list_display = ("organisation", "balance_usd", "created_at")
    search_fields = ("organisation__name",)
    inlines = [OrganisationWalletTransactionInline]

    def balance_usd(self, obj):
        return f"${obj.balance_usd_cents / 100:.2f}"
    balance_usd.short_description = "Balance (USD)"

@admin.register(OrganisationWalletTransaction)
class OrganisationWalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "transaction_type", "amount_usd", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("wallet__organisation__name", "description")

    def amount_usd(self, obj):
        return f"${obj.amount_cents / 100:.2f}"
    amount_usd.short_description = "Amount (USD)"

@admin.register(OrganisationPointAccount)
class OrganisationPointAccountAdmin(admin.ModelAdmin):
    list_display = ("organisation", "balance", "created_at")
    search_fields = ("organisation__name",)

@admin.register(ProductPointAccount)
class ProductPointAccountAdmin(admin.ModelAdmin):
    list_display = ("product", "balance", "created_at")
    search_fields = ("product__name",)

@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "product_account", "amount", "transaction_type", "created_at")
    search_fields = ("account__organisation__name", "product_account__product__name")
    list_filter = ("transaction_type",)

@admin.register(OrganisationPointGrant)
class OrganisationPointGrantAdmin(admin.ModelAdmin):
    list_display = ("organisation", "amount", "granted_by", "created_at")
    search_fields = ("organisation__name", "granted_by__username")

@admin.register(PlatformFeeConfiguration)
class PlatformFeeConfigurationAdmin(admin.ModelAdmin):
    list_display = ("percentage", "applies_from_date")
    ordering = ("-applies_from_date",)

class CartLineItemInline(admin.TabularInline):
    model = CartLineItem
    extra = 0
    readonly_fields = ("total_price_usd", "total_price_points")

    def total_price_usd(self, obj):
        return f"${obj.total_price_cents / 100:.2f}" if obj.total_price_cents else "$0.00"
    total_price_usd.short_description = "Total Price (USD)"

    def total_price_points(self, obj):
        return obj.total_price_points or 0
    total_price_points.short_description = "Total Price (Points)"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "organisation", "status", "created_at")
    inlines = [CartLineItemInline]

# Keep the CartLineItemAdmin as is

class SalesOrderLineItemInline(admin.TabularInline):
    model = SalesOrderLineItem
    extra = 0
    readonly_fields = ('total_price',)

    def total_price(self, obj):
        return f"${obj.total_price_cents / 100:.2f}" if obj.total_price_cents else "$0.00"
    total_price.short_description = "Total Price"

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'status', 'total_amount', 'created_at')
    list_filter = ('status',)
    search_fields = ('id', 'cart__id')
    inlines = [SalesOrderLineItemInline]

    def total_amount(self, obj):
        return f"${obj.total_usd_cents_including_fees_and_taxes / 100:.2f}"
    total_amount.short_description = "Total Amount"

@admin.register(SalesOrderLineItem)
class SalesOrderLineItemAdmin(admin.ModelAdmin):
    list_display = ("sales_order", "quantity", "unit_price", "total_price")
    search_fields = ("sales_order__id",)

    def unit_price(self, obj):
        return f"${obj.unit_price_cents / 100:.2f}" if obj.unit_price_cents else "$0.00"
    unit_price.short_description = "Unit Price"

    def total_price(self, obj):
        return f"${obj.total_price_cents / 100:.2f}" if obj.total_price_cents else "$0.00"
    total_price.short_description = "Total Price"

@admin.register(PointOrder)
class PointOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "status", "created_at", "total_points")
    list_filter = ("status",)
    search_fields = ("id", "cart__id")

    def total_points(self, obj):
        return obj.total_points if hasattr(obj, 'total_points') else 0
    total_points.short_description = "Total Points"
