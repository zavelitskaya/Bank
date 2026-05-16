from django.urls import path
from . import views

urlpatterns = [
    # Главная страница = список договоров
    path('', views.contracts_list, name='contracts_list'),
    
    # Детальная страница договора
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    
    # Страница заявки (корзины)
    path('account-request/<int:request_id>/', views.account_request_detail, name='account_request_detail'),
]