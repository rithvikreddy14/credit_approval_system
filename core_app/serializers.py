from rest_framework import serializers
from .models import Customer, Loan

# --- 1. /register ---

class CustomerRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=1)
    monthly_income = serializers.IntegerField(min_value=0)
    phone_number = serializers.CharField(max_length=15)

class CustomerResponseSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name', read_only=True)
    monthly_income = serializers.IntegerField(source='monthly_salary', read_only=True)
    
    class Meta:
        model = Customer
        fields = ('id', 'name', 'age', 'monthly_income', 'approved_limit', 'phone_number')

# --- 2. Loan Request (All Endpoints) ---

class LoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=1000)
    interest_rate = serializers.FloatField(min_value=0.01)
    tenure = serializers.IntegerField(min_value=1)
    
    def validate_customer_id(self, value):
        if not Customer.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Customer ID does not exist.")
        return value

# --- 3. /check-eligibility (Response) ---

class EligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField(allow_null=True)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()
    message = serializers.CharField(required=False, allow_null=True)

# --- 4. /create-loan (Response) ---

class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.FloatField()

# --- 5. /view-loan/loan_id (Response) ---

class CustomerMiniSerializer(serializers.ModelSerializer):
    """Nested serializer for customer details in /view-loan."""
    full_name = serializers.CharField(source='full_name', read_only=True)
    class Meta:
        model = Customer
        fields = ('id', 'first_name', 'last_name', 'phone_number', 'age', 'full_name')

class LoanDetailSerializer(serializers.ModelSerializer):
    """Serializer for /view-loan/<id> response body."""
    customer = CustomerMiniSerializer(read_only=True)
    
    class Meta:
        model = Loan
        fields = ('id', 'customer', 'loan_amount', 'interest_rate', 'monthly_installment', 'tenure')
        
# --- 6. /view-loans/customer_id (Response List Item) ---

class CustomerLoansSerializer(serializers.ModelSerializer):
    """Serializer for /view-loans/<id> list items."""
    repayments_left = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Loan
        fields = ('id', 'loan_amount', 'interest_rate', 'monthly_installment', 'repayments_left')