import pandas as pd
from datetime import date, datetime
from celery import shared_task
from django.db import transaction
from dateutil.relativedelta import relativedelta
from core_app.models import Customer, Loan, InitialDataIngestion
from core_app.services import calculate_approved_limit, calculate_monthly_installment

@shared_task
def ingest_initial_data(customer_filepath: str, loan_filepath: str):
    """
    Ingests customer and loan data from provided files into the database
    [cite_start]using background workers[cite: 35].
    """
    
    # Check if ingestion has already happened
    ingestion_status, created = InitialDataIngestion.objects.get_or_create(id=1)
    if ingestion_status.is_customer_data_ingested and ingestion_status.is_loan_data_ingested:
        print("Data already fully ingested. Skipping.")
        return 
        
    try:
        # --- Customer Data Ingestion ---
        if not ingestion_status.is_customer_data_ingested:
            print("Starting Customer Data Ingestion...")
            # Use 'Customer ID' for primary key to match loan data relationship
            df_customer = pd.read_csv(customer_filepath)
            df_customer.rename(columns={'Monthly Salary': 'monthly_salary', 'Approved Limit': 'approved_limit'}, inplace=True)
            
            customer_objects = []
            for _, row in df_customer.iterrows():
                customer_objects.append(
                    Customer(
                        id=row['Customer ID'],
                        first_name=row['First Name'],
                        last_name=row['Last Name'],
                        age=row['Age'],
                        phone_number=row['Phone Number'],
                        monthly_salary=row['monthly_salary'],
                        approved_limit=row['approved_limit'],
                    )
                )
            
            with transaction.atomic():
                Customer.objects.bulk_create(customer_objects, ignore_conflicts=True)
            
            ingestion_status.is_customer_data_ingested = True
            ingestion_status.save()
            print("Customer Data Ingestion Complete.")

        # --- Loan Data Ingestion ---
        if not ingestion_status.is_loan_data_ingested:
            print("Starting Loan Data Ingestion...")
            df_loan = pd.read_csv(loan_filepath)
            
            loan_objects = []
            debt_updates = {} 
            customers_data = {c.id: c for c in Customer.objects.all()}

            for _, row in df_loan.iterrows():
                cust_id = row['Customer ID']
                
                # Date Parsing
                start_date = datetime.strptime(row['Date of Approval'], '%Y-%m-%d').date()
                end_date = datetime.strptime(row['End Date'], '%Y-%m-%d').date()
                
                # Determine if the loan is currently active
                is_active = end_date > date.today()
                
                # Crude Debt Calculation (Required for initial customer debt/EMI fields)
                if is_active:
                    # Approximation: remaining tenure * monthly EMI.
                    months_passed = relativedelta(date.today(), start_date).years * 12 + relativedelta(date.today(), start_date).months
                    remaining_tenure = row['Tenure'] - months_passed
                    
                    if remaining_tenure > 0:
                        # Estimate remaining principal based on EMIs left (simplified)
                        remaining_debt_estimate = remaining_tenure * row['Monthly payment'] * 0.9 
                    else:
                        remaining_debt_estimate = 0
                else:
                    remaining_debt_estimate = 0

                loan_objects.append(
                    Loan(
                        customer_id=cust_id,
                        loan_amount=row['Loan Amount'],
                        tenure=row['Tenure'],
                        interest_rate=row['Interest Rate'],
                        monthly_installment=row['Monthly payment'],
                        emis_paid_on_time=row['EMIs paid on Time'],
                        start_date=start_date,
                        end_date=end_date,
                        is_current=is_active
                    )
                )

                if is_active:
                    if cust_id not in debt_updates:
                        debt_updates[cust_id] = {'debt': 0.0, 'emi': 0.0}
                        
                    debt_updates[cust_id]['debt'] += remaining_debt_estimate
                    debt_updates[cust_id]['emi'] += row['Monthly payment']

            with transaction.atomic():
                Loan.objects.bulk_create(loan_objects, ignore_conflicts=True)
                
                # Update Customer current_debt and total_monthly_emi
                for cust_id, data in debt_updates.items():
                    Customer.objects.filter(id=cust_id).update(
                        current_debt=models.F('current_debt') + data['debt'],
                        total_monthly_emi=models.F('total_monthly_emi') + data['emi']
                    )
            
            ingestion_status.is_loan_data_ingested = True
            ingestion_status.save()
            print("Loan Data Ingestion Complete.")

    except Exception as e:
        print(f"An error occurred during data ingestion: {e}")
        # In a real system, you'd log the error and mark the task as failed.

def start_ingestion_if_needed():
    """Starts the ingestion task if the DB is available."""
    try:
        if not InitialDataIngestion.objects.exists() or not InitialDataIngestion.objects.get(id=1).is_loan_data_ingested:
            ingest_initial_data.delay('customer_data.xlsx', 'loan_data.xlsx')
    except Exception as e:
        # Catch exceptions during initial DB check (e.g., table not created yet)
        pass