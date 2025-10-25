# 🏦 Alemeno Backend Internship Assignment: Credit Approval System

This project implements a Credit Approval System backend using **Django 4+**, **Django Rest Framework (DRF)**, **PostgreSQL**, and **Celery/Redis** for asynchronous data ingestion.  
The entire application is containerized using Docker Compose.

---

## 🚀 Launch Services

Start all four services (DB, Redis, Web, Worker) in detached mode.

```bash
docker compose up -d
```

### 🚀 Verify Ingestion

Monitor the celery_worker logs to ensure the initial data is loaded into the database. This process starts automatically.

```bash
docker compose logs celery_worker
```

Look for the "Complete" messages for both Customer and Loan Data.

---

## 💻 API Endpoints Documentation

All endpoints are hosted at the root path (/). Use an API client (like Postman or Insomnia) for testing.

### 1. Register New Customer

| Detail | Description |
|--------|-------------|
| **Endpoint** | `POST /register` |
| **Function** | Adds a new customer. Automatically calculates approved_limit as 36 × monthly_salary (rounded to nearest lakh). |

**Request Body**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 100000,
    "phone_number": "9876543210"
}
```

**Successful Response (201 Created)**
```json
{
    "id": 301,
    "name": "John Doe",
    "age": 30,
    "monthly_income": 100000,
    "approved_limit": 3600000,
    "phone_number": "9876543210"
}
```

---

### 2. Check Loan Eligibility

| Detail | Description |
|--------|-------------|
| **Endpoint** | `POST /check-eligibility` |
| **Function** | Calculates credit score (0–100), checks EMI limits, and determines approval and the corrected interest rate slab. |

**Request Body**
```json
{
    "customer_id": 14,
    "loan_amount": 500000,
    "interest_rate": 8.0,
    "tenure": 12
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | int | ID of the customer. |
| `approval` | bool | True if eligible, False otherwise. |
| `interest_rate` | float | The requested interest rate. |
| `corrected_interest_rate` | float | The rate applied based on credit score. |
| `tenure` | int | Tenure of the loan (in months). |
| `monthly_installment` | float | Calculated EMI using the corrected_interest_rate. |

---

### 3. Create Loan

| Detail | Description |
|--------|-------------|
| **Endpoint** | `POST /create-loan` |
| **Function** | Runs eligibility checks. If approved, creates a new Loan record and updates the customer's current_debt and total_monthly_emi. |

**Request Body**  
Same as `/check-eligibility`.

**Successful Response (200 OK - Approved)**
```json
{
    "loan_id": 1001,
    "customer_id": 14,
    "loan_approved": true,
    "message": "Loan successfully approved and created.",
    "monthly_installment": 43500.55
}
```

**Failure Response (200 OK - Rejected)**
```json
{
    "loan_id": null,
    "customer_id": 14,
    "loan_approved": false,
    "message": "Total EMI (including new loan) exceeds 50% of monthly salary, loan rejected.",
    "monthly_installment": 43500.55
}
```

---

### 4. View Loan Details

| Detail | Description |
|--------|-------------|
| **Endpoint** | `GET /view-loan/{loan_id}` |
| **Function** | Fetches detailed information about a single loan and its associated customer. |

**Response Body (200 OK)**  
Includes loan details and nested JSON for customer details.

---

### 5. View Customer Loans

| Detail | Description |
|--------|-------------|
| **Endpoint** | `GET /view-loans/{customer_id}` |
| **Function** | Returns a list of all active loans for the specified customer. |

**Response Item Fields**

| Field | Type | Description |
|-------|------|-------------|
| `loan_id` | int | ID of the approved loan. |
| `loan_amount` | float | Approved loan amount. |
| `interest_rate` | float | Final approved interest rate. |
| `monthly_installment` | float | Monthly repayment amount. |
| `repayments_left` | int | Calculated number of EMIs remaining (based on current date and loan tenure/start date). |

---


