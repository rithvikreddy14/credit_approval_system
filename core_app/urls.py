from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register_customer, name='register_customer'),
    path('check-eligibility', views.check_eligibility, name='check_eligibility'),
    path('create-loan', views.create_loan, name='create_loan'),
    path('view-loan/<int:loan_id>', views.view_loan, name='view_loan'),
    path('view-loans/<int:customer_id>', views.view_loans, name='view_loans'),
]