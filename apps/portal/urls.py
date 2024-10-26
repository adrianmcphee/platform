from django.urls import path
from .views import dashboard, user, bounty, agreement, portal

app_name = 'portal'

urlpatterns = [
    # Dashboard
    path('portal/', dashboard.PortalDashboardView.as_view(), name='dashboard'),
    path('portal/dashboard/', portal.PortalDashboardView.as_view(), name="dashboard"),
    path('portal/product/<str:product_slug>/', dashboard.PortalDashboardView.as_view(), name='product-dashboard'),
    path('portal/product/<str:product_slug>/tab/<int:default_tab>/', portal.PortalProductDetailView.as_view(), name="product-detail"),

    # User Management
    path('portal/product/<str:product_slug>/users/', user.ManageUsersView.as_view(), name='manage-users'),
    path('portal/product/<str:product_slug>/users/add/', user.AddProductUserView.as_view(), name='add-user'),
    path('portal/product/<str:product_slug>/product-users/<int:pk>/update/', portal.UpdateProductUserView.as_view(), name="update-product-user"),

    # Bounty Management
    path('portal/bounties/', portal.ManageBountiesView.as_view(), name="manage-bounties"),
    path('portal/bounties/bounty-requests/', portal.BountyClaimRequestsView.as_view(), name="bounty-requests"),
    path('portal/bounties/action/<int:pk>/', portal.bounty_claim_actions, name="bounties-action"),
    path('portal/product/<str:product_slug>/dashboard/bounties/', portal.DashboardProductBountiesView.as_view(), name='dashboard-bounties'),
    path('portal/product/<str:product_slug>/dashboard/bounties/filter/', portal.DashboardProductBountyFilterView.as_view(), name='dashboard-bounty-filter'),
    path('portal/product/<str:product_slug>/review-work/', portal.ReviewWorkView.as_view(), name="review-work"),

    # Challenge Management
    path('portal/product/<str:product_slug>/challenges/', portal.DashboardProductChallengesView.as_view(), name="product-challenges"),
    path('portal/product/<str:product_slug>/challenges/filter/', portal.DashboardProductChallengeFilterView.as_view(), name="product-challenge-filter"),

    # Agreements
    path('portal/product/<str:product_slug>/agreements/', agreement.ContributorAgreementListView.as_view(), name='agreements'),
    path('portal/product/<str:product_slug>/agreements/create/', agreement.CreateContributorAgreementView.as_view(), name='create-agreement'),
    path('portal/product/<str:product_slug>/agreements/<str:pk>/', agreement.ContributorAgreementView.as_view(), name='contributor-agreement'),
    path('portal/product/<str:product_slug>/contributor-agreement-templates/', portal.ContributorAgreementTemplateListView.as_view(), name="contributor-agreement-templates"),
    path('portal/product/<str:product_slug>/contributor-agreement/<int:pk>/', portal.ContributorAgreementTemplateView.as_view(), name="contributor-agreement-template-detail"),
    path('portal/product/<str:product_slug>/contributor-agreement/create/', portal.CreateContributorAgreementTemplateView.as_view(), name="create-contributor-agreement-template"),

    # Product Settings
    path('portal/product-setting/<int:pk>/', portal.ProductSettingView.as_view(), name="product-setting"),
]
