from django.contrib import admin
from django.urls import path
from bmstu_lab import views

urlpatterns = [
    path('', views.contracts_list, name='contracts_list'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('contracts/<int:contract_id>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('contracts/<int:contract_id>/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('set-main-contract/<int:contract_id>/', views.set_main_contract, name='set_main_contract')
]