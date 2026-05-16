from django.shortcuts import render, get_object_or_404, redirect
from django.db import connection
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import BankContract, AccountRequest, RequestedContract
from minio import Minio
from django.conf import settings

# ============================================
# VIEWS ДЛЯ ЛАБОРАТОРНОЙ 2
# ============================================

def contracts_list(request):
    """Страница 1: список договоров + карточка корзины"""
    search_query = request.GET.get('search', '')
    
    contracts = BankContract.objects.filter(is_active=True)
    if search_query:
        contracts = contracts.filter(counterparty_name__icontains=search_query)
    
    # Добавляем URL изображений
    for contract in contracts:
        contract.image_url = f"http://localhost:9000/banking-images/{contract.image_key}"
        print(f"DEBUG: {contract.contract_number} -> image_url = {contract.image_url}")  # Отладка
    
    account_request = AccountRequest.objects.filter(
        status='DRAFT',
        creator_id=2
    ).first()
    
    cart_items_count = 0
    account_request_id = None
    if account_request:
        account_request_id = account_request.id
        cart_items_count = account_request.requested_contracts.count()
    
    context = {
        'contracts': contracts,
        'search_query': search_query,
        'account_request_id': account_request_id,
        'cart_items_count': cart_items_count,
    }
    return render(request, 'contracts/contracts_list.html', context)

def contract_detail(request, contract_id):
    """Страница 2: детальная информация о договоре"""
    contract = get_object_or_404(BankContract, id=contract_id, is_active=True)
    contract.image_url = f"http://localhost:9000/banking-images/{contract.image_key}"  # Добавьте эту строку
    return render(request, 'contracts/contract_detail.html', {
        'contract': contract,
    })

def account_request_detail(request, request_id):
    """Страница 3: просмотр заявки (корзины)"""
    account_request = get_object_or_404(AccountRequest, id=request_id, status='DRAFT')
    
    requested_contracts = account_request.requested_contracts.select_related('bank_contract').all()
    
    requested_contracts_with_details = []
    for item in requested_contracts:
        contract = item.bank_contract
        contract.image_url = f"http://localhost:9000/banking-images/{contract.image_key}"  # Добавьте эту строку
        requested_contracts_with_details.append({
            'contract': contract,
            'quantity': item.quantity,
        })
    
    context = {
        'account_request': account_request,
        'requested_contracts': requested_contracts_with_details,
    }
    return render(request, 'contracts/account_request_detail.html', context)
    
    context = {
        'account_request': account_request,
        'requested_contracts': requested_contracts_with_details,
    }
    return render(request, 'contracts/account_request_detail.html', context)


def delete_account_request(request, request_id):
    """Логическое удаление заявки через прямой SQL запрос (не ORM)"""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE contracts_accountrequest SET status = 'DELETED' WHERE id = %s AND status = 'DRAFT'",
            [request_id]
        )
    messages.success(request, 'Заявка удалена')
    return redirect('contracts_list')


def set_primary_contract(request, request_id, contract_id):
    """Установка основного договора для счета"""
    if request.method == 'POST':
        account_request = get_object_or_404(AccountRequest, id=request_id, status='DRAFT')
        contract = get_object_or_404(BankContract, id=contract_id)
        
        account_request.primary_contract = contract
        account_request.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


def submit_account_request(request, request_id):
    """Создание заявки (меняем статус с DRAFT на SUBMITTED)"""
    if request.method == 'POST':
        account_request = get_object_or_404(AccountRequest, id=request_id, status='DRAFT')
        
        # Проверяем, что основной договор выбран
        if not account_request.primary_contract:
            messages.error(request, 'Выберите основной договор')
            return redirect('account_request_detail', request_id=request_id)
        
        # Обновляем статус и дату формирования
        account_request.status = 'SUBMITTED'
        account_request.submitted_at = timezone.now()
        account_request.save()
        
        messages.success(request, 'Заявка успешно создана')
        return redirect('contracts_list')
    return redirect('contracts_list')


def remove_from_request(request, contract_id):
    """Удаление договора из заявки"""
    if request.method == 'POST':
        account_request = AccountRequest.objects.filter(status='DRAFT', creator_id=2).first()
        if account_request:
            # Удаляем связь
            RequestedContract.objects.filter(
                account_request=account_request,
                bank_contract_id=contract_id
            ).delete()
            messages.success(request, 'Договор удалён из заявки')
            return redirect('account_request_detail', request_id=account_request.id)
    return redirect('contracts_list')

def get_image_url(image_key):
    """Получить прямую ссылку на изображение из публичного bucket"""
    if not image_key:
        return None
    return f"http://localhost:9000/banking-images/{image_key}"