from rest_framework import serializers
from .models import BankContract, AccountRequest, RequestedContract

class BankContractSerializer(serializers.ModelSerializer):
    contract_type_display = serializers.CharField(source='get_contract_type_display', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BankContract
        fields = ['id', 'contract_number', 'contract_type', 'contract_type_display', 
                  'counterparty_name', 'description', 'image_key', 'image_url', 'is_active']
    
    def get_image_url(self, obj):
        if obj.image_key:
            return f"http://localhost:9000/banking-images/{obj.image_key}"
        return None


class RequestedContractSerializer(serializers.ModelSerializer):
    contract_details = BankContractSerializer(source='bank_contract', read_only=True)
    
    class Meta:
        model = RequestedContract
        fields = ['id', 'bank_contract', 'contract_details', 'quantity']


class AccountRequestSerializer(serializers.ModelSerializer):
    creator = serializers.StringRelatedField(read_only=True)
    moderator = serializers.StringRelatedField(read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    moderator_name = serializers.CharField(source='moderator.username', read_only=True)
    requested_contracts = RequestedContractSerializer(many=True, read_only=True)  # Убрали source
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_code_display', read_only=True)
    
    class Meta:
        model = AccountRequest
        fields = ['id', 'status', 'status_display', 'created_at', 'submitted_at', 'completed_at',
                  'creator', 'creator_name', 'moderator', 'moderator_name',
                  'balance_account_number', 'currency_code', 'currency_display',
                  'primary_contract', 'assigned_account_number', 'requested_contracts']
        read_only_fields = ['id', 'created_at', 'submitted_at', 'completed_at', 
                           'creator', 'moderator', 'assigned_account_number']