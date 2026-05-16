from django.urls import path
from . import views

urlpatterns = [
    path('', views.contracts_list, name='contracts_list'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('account-request/<int:request_id>/', views.account_request_detail, name='account_request_detail'),
    path('account-request/<int:request_id>/delete/', views.delete_account_request, name='delete_account_request'),
    path('account-request/<int:request_id>/set-primary/<int:contract_id>/', views.set_primary_contract, name='set_primary_contract'),
    path('account-request/<int:request_id>/submit/', views.submit_account_request, name='submit_account_request'),
    path('request/remove/<int:contract_id>/', views.remove_from_request, name='remove_from_request'),
]