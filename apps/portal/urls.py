from django.urls import path
from .views.dashboard import PortalDashboardView
from .views.user import ManageUsersView, AddProductUserView
from .views.bounty import ManageBountiesView, ReviewWorkView
from .views.agreement import (
    ContributorAgreementView,
    ContributorAgreementListView,
    CreateContributorAgreementView
)

app_name = 'portal'

urlpatterns = [

   # Dashboard
    path('', PortalDashboardView.as_view(), name='dashboard'),
    path('product/<str:product_slug>/', PortalDashboardView.as_view(), name='product-dashboard'),
    path('product/<str:product_slug>/dashboard/bounties/', DashboardProductBountiesView.as_view(), name='dashboard-bounties'),
    path('product/<str:product_slug>/dashboard/bounties/filter/', DashboardProductBountyFilterView.as_view(), name='dashboard-bounty-filter'),

    # User Management
    path('product/<str:product_slug>/users/', ManageUsersView.as_view(), name='manage-users'),
    path('product/<str:product_slug>/users/add/', AddProductUserView.as_view(), name='add-user'),
    
    # Bounty Management
    path('bounties/', ManageBountiesView.as_view(), name='my-bounties'),
    path('product/<str:product_slug>/review/', ReviewWorkView.as_view(), name='review-work'),
    
    # Agreements
    path('product/<str:product_slug>/agreements/', ContributorAgreementListView.as_view(), name='agreements'),
    path('product/<str:product_slug>/agreements/create/', CreateContributorAgreementView.as_view(), name='create-agreement'),
    path('product/<str:product_slug>/agreements/<str:pk>/', ContributorAgreementView.as_view(), name='contributor-agreement'),
