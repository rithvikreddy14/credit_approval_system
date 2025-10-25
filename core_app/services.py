import math
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, F
from django.db import models
from .models import Customer, Loan

# --------------------
# A. Financial Calculations
# --------------------

def calculate_approved_limit(monthly_salary: int) -> int:
    """Calculates approved limit (36 * monthly_salary) rounded to the nearest lakh."""
    limit = 36 * monthly_salary
    rounded_limit = round(limit / 100000) * 100000 
    return int(rounded_limit)

def calculate_monthly_installment(loan_amount: float, interest_rate: float, tenure: int) -> float:
    """Calculates EMI using the compound interest scheme (PMT formula)."""
    monthly_rate = (interest_rate / 12) / 100
    
    if monthly_rate <= 0:
        return round(loan_amount / tenure, 2)
    
    # PMT (EMI) = P * r * (1 + r)^n / ((1 + r)^n - 1)
    numerator = monthly_rate * ((1 + monthly_rate) ** tenure)
    denominator = ((1 + monthly_rate) ** tenure) - 1
    
    emi = loan_amount * (numerator / denominator)
    return round(emi, 2)

# --------------------
# B. Credit Score and Eligibility
# --------------------

def calculate_credit_score(customer_id: int) -> int:
    """Calculates the customer's credit score based on loan history."""
    try:
        customer = Customer.objects.get(pk=customer_id)
        loans = Loan.objects.filter(customer=customer)
    except Customer.DoesNotExist:
        return 0 
        
    score = 100 
    
    # Check for over-indebtedness first (highest priority, sets score to 0)
    current_loan_sum = loans.filter(is_current=True).aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
    if current_loan_sum > customer.approved_limit:
        customer.credit_score = 0
        customer.save()
        return 0 

    # i. Past Loans paid on time (if emis_paid_on_time >= tenure for closed loans)
    paid_on_time_count = loans.filter(is_current=False, emis_paid_on_time__gte=F('tenure')).count()
    score += paid_on_time_count * 10 
    
    # ii. No of loans taken in past (more loans = risk, but repaid loans are good)
    total_loans = loans.count()
    score -= total_loans * 2
    
    # Check for active loans with poor repayment history (major negative)
    bad_loans_count = loans.filter(is_current=True, emis_paid_on_time__lt=models.F('tenure') / 2).count()
    score -= bad_loans_count * 25 # High penalty

    # iii. Loan activity in current year (More activity means lower score boost)
    current_year = date.today().year
    active_in_current_year = loans.filter(start_date__year=current_year).count()
    score -= active_in_current_year * 3

    # iv. Loan approved volume (large volume repaid successfully)
    total_paid_volume = loans.filter(is_current=False).aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
    score += int(total_paid_volume / 2000000)

    # Clamp score between 0 and 100
    final_score = max(0, min(100, score))

    customer.credit_score = final_score
    customer.save()
    return final_score

def check_loan_eligibility(customer: Customer, requested_loan_amount: float, requested_interest_rate: float, tenure: int) -> dict:
    """Performs all eligibility checks and returns decision and corrected rate."""

    score = customer.credit_score 
    approval = False
    corrected_interest_rate = requested_interest_rate
    message = None
    
    # 1. Calculate potential EMI and check EMI to salary ratio
    max_emi_limit = customer.monthly_salary * 0.5
    potential_emi = calculate_monthly_installment(requested_loan_amount, requested_interest_rate, tenure)
    total_current_and_new_emi = customer.total_monthly_emi + potential_emi
    
    if total_current_and_new_emi > max_emi_limit:
        return {
            "customer_id": customer.id,
            "approval": False,
            "interest_rate": requested_interest_rate,
            "corrected_interest_rate": None,
            "tenure": tenure,
            "monthly_installment": potential_emi,
            "message": "Total EMI (including new loan) exceeds 50% of monthly salary, loan rejected."
        }

    # 2. Determine approval status and required interest rate slab
    if score > 50:
        approval = True
        min_required_rate = 0 
        corrected_rate_slab = requested_interest_rate
    elif 50 >= score > 30:
        approval = True
        min_required_rate = 12.01 
        corrected_rate_slab = 12.0
    elif 30 >= score > 10:
        approval = True
        min_required_rate = 16.01 
        corrected_rate_slab = 16.0
    else: # score <= 10
        approval = False
        message = "Credit score too low (≤ 10), don't approve any loans."

    # 3. Apply Interest Rate Correction if Approved
    if approval and requested_interest_rate < min_required_rate:
        corrected_interest_rate = corrected_rate_slab
    
    final_monthly_installment = calculate_monthly_installment(
        requested_loan_amount, corrected_interest_rate, tenure
    )
    
    response = {
        "customer_id": customer.id,
        "approval": approval,
        "interest_rate": requested_interest_rate,
        "corrected_interest_rate": corrected_interest_rate,
        "tenure": tenure,
        "monthly_installment": final_monthly_installment,
    }
    
    if not approval:
         response['message'] = message

    return response