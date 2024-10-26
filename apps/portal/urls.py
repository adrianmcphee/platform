from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('product/<str:product_slug>/', views.DashboardView.as_view(), name='product-dashboard'),
    path('product/<str:product_slug>/tab/<int:default_tab>/', views.PortalProductDetailView.as_view(), name="product-detail"),

    # User Management
    path('product/<str:product_slug>/users/', views.ManageUsersView.as_view(), name='manage-users'),
    path('product/<str:product_slug>/users/add/', views.AddProductUserView.as_view(), name='add-user'),
    path('product/<str:product_slug>/product-users/<int:pk>/update/', views.UpdateProductUserView.as_view(), name="update-product-user"),

    # Bounty Management
    path('bounties/', views.ManageBountiesView.as_view(), name="manage-bounties"),
    path('bounties/bounty-requests/', views.PortalBountyClaimRequestsView.as_view(), name="bounty-requests"),
    path('bounties/action/<int:pk>/', views.bounty_claim_actions, name="bounties-action"),
    path('product/<str:product_slug>/bounties/', views.PortalProductBountiesView.as_view(), name='product-bounties'),
    path('product/<str:product_slug>/bounties/filter/', views.PortalProductBountyFilterView.as_view(), name='product-bounty-filter'),
    path('product/<str:product_slug>/review-work/', views.PortalReviewWorkView.as_view(), name="review-work"),

    # Challenge Management
    path('product/<str:product_slug>/challenges/', views.PortalProductChallengesView.as_view(), name="product-challenges"),
    path('product/<str:product_slug>/challenges/filter/', views.PortalProductChallengeFilterView.as_view(), name="product-challenge-filter"),

    # Contributor Agreement Templates
    path('product/<str:product_slug>/contributor-agreement-templates/', views.PortalContributorAgreementTemplateListView.as_view(), name="contributor-agreement-templates"),

    # Product Settings
    path('product-setting/<int:pk>/', views.ProductSettingView.as_view(), name="product-setting"),
]
