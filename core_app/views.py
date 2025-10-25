from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from dateutil.relativedelta import relativedelta
from datetime import date

from .models import Customer, Loan
from .serializers import (
    CustomerRegisterSerializer, CustomerResponseSerializer, LoanRequestSerializer,
    EligibilityResponseSerializer, CreateLoanResponseSerializer, LoanDetailSerializer,
    CustomerLoansSerializer
)
from .services import calculate_approved_limit, calculate_credit_score, check_loan_eligibility

# --- 1. /register ---
@api_view(['POST'])
def register_customer(request):
    serializer = CustomerRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    approved_limit = calculate_approved_limit(data['monthly_income'])
    
    try:
        customer = Customer.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=data['monthly_income'],
            approved_limit=approved_limit,
        )
        
        response_serializer = CustomerResponseSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        if 'phone_number' in str(e):
             return Response({"message": "Customer with this phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 2. /check-eligibility ---
@api_view(['POST'])
def check_eligibility(request):
    request_serializer = LoanRequestSerializer(data=request.data)
    if not request_serializer.is_valid():
        return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = request_serializer.validated_data
    
    customer = Customer.objects.get(pk=data['customer_id'])
    
    # Recalculate credit score before checking eligibility
    calculate_credit_score(customer.id) # Updates customer.credit_score
    
    eligibility_result = check_loan_eligibility(
        customer=customer,
        requested_loan_amount=data['loan_amount'],
        requested_interest_rate=data['interest_rate'],
        tenure=data['tenure']
    )
    
    response_serializer = EligibilityResponseSerializer(eligibility_result)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


# --- 3. /create-loan ---
@api_view(['POST'])
def create_loan(request):
    request_serializer = LoanRequestSerializer(data=request.data)
    if not request_serializer.is_valid():
        return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = request_serializer.validated_data
    customer = Customer.objects.get(pk=data['customer_id'])
    
    # Check Eligibility
    calculate_credit_score(customer.id) 
    eligibility_result = check_loan_eligibility(
        customer=customer,
        requested_loan_amount=data['loan_amount'],
        requested_interest_rate=data['interest_rate'],
        tenure=data['tenure']
    )
    
    loan_approved = eligibility_result['approval']
    monthly_installment = eligibility_result['monthly_installment']
    
    if loan_approved:
        corrected_interest_rate = eligibility_result['corrected_interest_rate']
        
        with transaction.atomic():
            # Create the Loan Record
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=data['loan_amount'],
                tenure=data['tenure'],
                interest_rate=corrected_interest_rate,
                monthly_installment=monthly_installment,
                emis_paid_on_time=0,
                start_date=date.today(),
                end_date=date.today() + relativedelta(months=+data['tenure']),
                is_current=True
            )
            
            # Update Customer Debt
            customer.current_debt += data['loan_amount'] # Crude debt update
            customer.total_monthly_emi += monthly_installment
            customer.save()
            
            response_data = {
                "loan_id": loan.id,
                "customer_id": customer.id,
                "loan_approved": True,
                "message": "Loan successfully approved and created.",
                "monthly_installment": monthly_installment,
            }
        
    else:
        response_data = {
            "loan_id": None,
            "customer_id": customer.id,
            "loan_approved": False,
            "message": eligibility_result.get('message', 'Loan not approved due to eligibility constraints.'),
            "monthly_installment": monthly_installment,
        }

    response_serializer = CreateLoanResponseSerializer(response_data)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


# --- 4. /view-loan/<loan_id> ---
@api_view(['GET'])
def view_loan(request, loan_id):
    try:
        loan = Loan.objects.select_related('customer').get(pk=loan_id)
    except Loan.DoesNotExist:
        return Response({"message": "Loan not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)


# --- 5. /view-loans/<customer_id> ---
@api_view(['GET'])
def view_loans(request, customer_id):
    try:
        Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return Response({"message": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
    
    loans = Loan.objects.filter(customer_id=customer_id, is_current=True)
    serializer = CustomerLoansSerializer(loans, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)