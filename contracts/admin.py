from django.contrib import admin
from .models import BankContract, AccountRequest, RequestedContract

@admin.register(BankContract)
class BankContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'contract_type', 'counterparty_name')
    search_fields = ('contract_number', 'counterparty_name')

@admin.register(AccountRequest)
class AccountRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'creator', 'primary_contract', 'currency_code')
    list_filter = ('status', 'currency_code')
    raw_id_fields = ('primary_contract',)

@admin.register(RequestedContract)
class RequestedContractAdmin(admin.ModelAdmin):
    list_display = ('account_request', 'bank_contract', 'connection_date', 'comment')
    list_filter = ('connection_date',)