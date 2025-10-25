from django.db import models
from datetime import date
from dateutil.relativedelta import relativedelta

# Helper for initial data ingestion (not explicitly asked for, but useful)
class InitialDataIngestion(models.Model):
    is_customer_data_ingested = models.BooleanField(default=False)
    is_loan_data_ingested = models.BooleanField(default=False)
    ingestion_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ingestion Status: Customer={self.is_customer_data_ingested}, Loan={self.is_loan_data_ingested}"

class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    monthly_salary = models.IntegerField()
    age = models.IntegerField(null=True) 
    approved_limit = models.IntegerField() 

    current_debt = models.FloatField(default=0)
    total_monthly_emi = models.FloatField(default=0)
    credit_score = models.IntegerField(default=0) 

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.FloatField()
    tenure = models.IntegerField() # In months
    interest_rate = models.FloatField() 
    monthly_installment = models.FloatField()
    
    emis_paid_on_time = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    
    is_current = models.BooleanField(default=True) 

    def __str__(self):
        return f"Loan {self.id} for Customer {self.customer.id}"

    @property
    def repayments_left(self):
        if not self.is_current:
             return 0
        # Calculate remaining EMIs based on today's date vs start/end date
        months_passed = relativedelta(date.today(), self.start_date).years * 12 + relativedelta(date.today(), self.start_date).months
        
        # Ensure we don't return a negative or more than the loan tenure
        if months_passed >= self.tenure:
            return 0
            
        return self.tenure - months_passed