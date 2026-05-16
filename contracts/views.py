from django.shortcuts import render

# ============================================
# ДАННЫЕ В ПАМЯТИ (БЕЗ БАЗЫ ДАННЫХ)
# ============================================

# Услуги = банковские договоры
BANK_CONTRACTS = [
    {
        'id': 1,
        'contract_number': 'РКО-001/2025',
        'contract_type': 'РКО',
        'counterparty_name': 'ООО "Центр кибернетической интеграции"',
        'price': 1500.00,
        'description': 'Расчетно-кассовое обслуживание для малого бизнеса. Включает до 100 бесплатных платежей в месяц.',
        'image_key': 'rko.png',
    },
    {
        'id': 2,
        'contract_number': 'ЗП-002/2025',
        'contract_type': 'Зарплатный проект',
        'counterparty_name': 'ООО "ТехноИнтеграция"',
        'price': 5000.00,
        'description': 'Зарплатный проект для компаний до 500 сотрудников. Выгрузка реестров в день зарплаты.',
        'image_key': 'salary.png',
    },
    {
        'id': 3,
        'contract_number': 'ЭК-003/2025',
        'contract_type': 'Эквайринг',
        'counterparty_name': 'ИП Иванов А.С.',
        'price': 2500.00,
        'description': 'Торговый эквайринг. Ставка 1.8% от оборота. Терминал в подарок.',
        'image_key': 'acquiring.png',
    },
]

# Заявка-черновик (у пользователя только одна)
ACCOUNT_REQUEST_DRAFT = {
    'id': 1,
    'status': 'DRAFT',
    'balance_account_number': '40802810',
    'currency_code': '810',
    'result_account_number': '',
    'requested_contracts': [
        {'contract_id': 1, 'quantity': 1},
        {'contract_id': 3, 'quantity': 2},
    ]
}


# ============================================
# VIEWS (ТОЛЬКО GET, БЕЗ СЕССИЙ)
# ============================================

def contracts_list(request):
    """Страница 1: список договоров + карточка корзины"""
    search_query = request.GET.get('search', '')
    
    contracts = BANK_CONTRACTS.copy()
    if search_query:
        contracts = [c for c in contracts 
                    if search_query.lower() in c['counterparty_name'].lower()]
    
    cart_items_count = len(ACCOUNT_REQUEST_DRAFT['requested_contracts'])
    
    context = {
        'contracts': contracts,
        'search_query': search_query,
        'account_request_id': ACCOUNT_REQUEST_DRAFT['id'],
        'cart_items_count': cart_items_count,
    }
    return render(request, 'contracts/contracts_list.html', context)


def contract_detail(request, contract_id):
    """Страница 2: детальная информация о договоре"""
    # Ручной поиск в списке (без БД)
    contract = None
    for c in BANK_CONTRACTS:
        if c['id'] == contract_id:
            contract = c
            break
    
    if not contract:
        return render(request, '404.html', status=404)
    
    return render(request, 'contracts/contract_detail.html', {
        'contract': contract,
    })


def account_request_detail(request, request_id):
    """Страница 3: просмотр заявки (корзины)"""
    if request_id != ACCOUNT_REQUEST_DRAFT['id']:
        return render(request, '404.html', status=404)
    
    requested_contracts_with_details = []
    for item in ACCOUNT_REQUEST_DRAFT['requested_contracts']:
        contract = None
        for c in BANK_CONTRACTS:
            if c['id'] == item['contract_id']:
                contract = c
                break
        if contract:
            requested_contracts_with_details.append({
                'contract': contract,
                'quantity': item['quantity'],
            })
    
    context = {
        'account_request': ACCOUNT_REQUEST_DRAFT,
        'requested_contracts': requested_contracts_with_details,
    }
    return render(request, 'contracts/account_request_detail.html', context)