from django.urls import path, re_path

from .views import bounties, challenges, products, initiatives, portal, ideas_bugs, product_areas
from .views.product_area_admin import get_nodes, move_node

urlpatterns = [
    # Bounty-related URLs
    path("bounties/", bounties.BountyListView.as_view(), name="bounties"),
    path("<str:product_slug>/bounties/", bounties.ProductBountyListView.as_view(), name="product_bounties"),
    path("<str:product_slug>/challenge/<int:challenge_id>/bounty/<int:pk>/", bounties.BountyDetailView.as_view(), name="bounty-detail"),
    path("<str:product_slug>/challenge/<int:challenge_id>/bounty/create/", bounties.CreateBountyView.as_view(), name="create-bounty"),
    path("<str:product_slug>/challenge/<int:challenge_id>/bounty/update/<int:pk>/", bounties.UpdateBountyView.as_view(), name="update-bounty"),
    path("<str:product_slug>/challenge/<int:challenge_id>/bounty/delete/<int:pk>/", bounties.DeleteBountyView.as_view(), name="delete-bounty"),
    # path("bounty-claim/<int:pk>/", bounties.BountyClaimView.as_view(), name="bounty-claim"),
    path("bounty-claim/delete/<int:pk>/", bounties.DeleteBountyClaimView.as_view(), name="delete-bounty-claim"),

    # Challenge-related URLs
    re_path(r"^challenges/.*$", challenges.redirect_challenge_to_bounties, name="challenges"),
    path("<str:product_slug>/challenge/create/", challenges.CreateChallengeView.as_view(), name="create-challenge"),
    path("<str:product_slug>/challenge/update/<int:pk>/", challenges.UpdateChallengeView.as_view(), name="update-challenge"),
    path("<str:product_slug>/challenge/delete/<int:pk>/", challenges.DeleteChallengeView.as_view(), name="delete-challenge"),
    path("<str:product_slug>/challenge/<int:pk>/", challenges.ChallengeDetailView.as_view(), name="challenge_detail"),
    path("<str:product_slug>/challenges/", challenges.ProductChallengesView.as_view(), name="product_challenges"),

    # Product-related URLs
    path("products/", products.ProductListView.as_view(), name="products"),
    path("product/create/", products.CreateProductView.as_view(), name="create-product"),
    path("product/update/<int:pk>/", products.UpdateProductView.as_view(), name="update-product"),
    path("product/<str:product_slug>/", products.ProductRedirectView.as_view(), name="product_detail"),
    path("<str:product_slug>/summary/", products.ProductSummaryView.as_view(), name="product_summary"),
    path("<str:product_slug>/tree/", products.ProductTreeInteractiveView.as_view(), name="product_tree"),
    path("<str:product_slug>/people/", products.ProductRoleAssignmentView.as_view(), name="product_people"),
    path("organisation/create/", products.CreateOrganisationView.as_view(), name="create-organisation"),

    # Initiative-related URLs
    path("<str:product_slug>/initiatives/", initiatives.ProductInitiativesView.as_view(), name="product_initiatives"),
    path("<str:product_slug>/initiative/create/", initiatives.CreateInitiativeView.as_view(), name="create-initiative"),
    path("<str:product_slug>/initiative/<int:pk>/", initiatives.InitiativeDetailView.as_view(), name="initiative_detail"),

    # Portal (formerly Dashboard) URLs
    path("portal/", portal.PortalDashboardView.as_view(), name="dashboard-home"),
    path("portal/product/<str:product_slug>/<int:default_tab>/", portal.PortalDashboardView.as_view(), name="product-portal"),
    path("portal/home/", portal.PortalDashboardView.as_view(), name="portal-home"),
    path("portal/bounties/", portal.ManageBountiesView.as_view(), name="manage-bounties"),
    path("portal/bounties/bounty-requests/", portal.BountyClaimRequestsView.as_view(), name="portal-bounty-requests"),
    path("portal/product/<str:product_slug>/tab/<int:default_tab>/", portal.PortalProductDetailView.as_view(), name="portal-product-detail"),
    path("portal/product/<str:product_slug>/challenges/", portal.DashboardProductChallengesView.as_view(), name="portal-product-challenges"),
    path("portal/product/<str:product_slug>/challenges/filter/", portal.DashboardProductChallengeFilterView.as_view(), name="portal-product-challenge-filter"),
    path("portal/product/<str:product_slug>/bounties/", portal.DashboardProductBountiesView.as_view(), name="portal-product-bounties"),
    path("portal/bounties/action/<int:pk>/", portal.bounty_claim_actions, name="portal-bounties-action"),
    path("portal/product/<str:product_slug>/bounties/filter/", portal.DashboardProductBountyFilterView.as_view(), name="portal-product-bounty-filter"),
    path("portal/product/<str:product_slug>/review-work/", portal.ReviewWorkView.as_view(), name="portal-review-work"),
    path("portal/product/<str:product_slug>/contributor-agreement-templates/", portal.ContributorAgreementTemplateListView.as_view(), name="portal-contributor-agreement-templates"),
    path("portal/product/<str:product_slug>/user-management/", portal.ManageUsersView.as_view(), name="manage-users"),
    path("portal/product/<str:product_slug>/add-product-user/", portal.AddProductUserView.as_view(), name="add-product-user"),
    path("portal/product/<str:product_slug>/product-users/<int:pk>/update/", portal.UpdateProductUserView.as_view(), name="update-product-user"),
    path("portal/product-setting/<int:pk>/", portal.ProductSettingView.as_view(), name="product-setting"),

    # Ideas and Bugs URLs
    path("<str:product_slug>/ideas-and-bugs/", ideas_bugs.ProductIdeasAndBugsView.as_view(), name="product_ideas_bugs"),
    path("<str:product_slug>/idea-list/", ideas_bugs.ProductIdeaListView.as_view(), name="product_idea_list"),
    path("<str:product_slug>/bug-list/", ideas_bugs.ProductBugListView.as_view(), name="product_bug_list"),
    path("<str:product_slug>/ideas/new/", ideas_bugs.CreateProductIdea.as_view(), name="add_product_idea"),
    path("<str:product_slug>/idea/<int:pk>/", ideas_bugs.ProductIdeaDetail.as_view(), name="product_idea_detail"),
    path("<str:product_slug>/ideas/update/<int:pk>/", ideas_bugs.UpdateProductIdea.as_view(), name="update_product_idea"),
    path("<str:product_slug>/bugs/new/", ideas_bugs.CreateProductBug.as_view(), name="add_product_bug"),
    path("<str:product_slug>/bug/<int:pk>/", ideas_bugs.ProductBugDetail.as_view(), name="product_bug_detail"),
    path("<str:product_slug>/bugs/update/<int:pk>/", ideas_bugs.UpdateProductBug.as_view(), name="update_product_bug"),
    path("cast-vote-for-idea/<int:pk>/", ideas_bugs.cast_vote_for_idea, name="cast-vote-for-idea"),

    # Product Areas URLs
    path("<str:product_slug>/product-areas/", product_areas.ProductAreaCreateView.as_view(), name="product_area"),
    path("<str:product_slug>/product-areas/<int:pk>/update/", product_areas.ProductAreaUpdateView.as_view(), name="product_area_update"),
    path("<str:product_slug>/product-areas/<int:pk>/detail/", product_areas.ProductAreaDetailView.as_view(), name="product_area_detail"),
    path("<str:product_slug>/capability/create/", product_areas.CreateCapabilityView.as_view(), name="create-capability"),

    # Contributor Agreement URLs
    path("<str:product_slug>/contributor-agreement/<int:pk>/", portal.ContributorAgreementTemplateView.as_view(), name="contributor-agreement-template-detail"),
    path("<str:product_slug>/contributor-agreement/create/", portal.CreateContributorAgreementTemplateView.as_view(), name="create-contributor-agreement-template"),
    path('admin/product_management/productarea/get_nodes/', get_nodes, name='get_product_area_nodes'),
    path('admin/product_management/productarea/<str:node_id>/move/', move_node, name='move_product_area_node'),
]
