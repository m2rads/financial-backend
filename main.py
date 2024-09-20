import os
import certifi
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union, Tuple
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
import calendar
from datetime import date
import requests
import time
import base64

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Configure Plaid client
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': os.getenv('PLAID_CLIENT_ID'),
        'secret': os.getenv('PLAID_SECRET'),
    }
)

# Use certifi's bundle of root certificates
configuration.ssl_ca_cert = certifi.where()

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

class PublicToken(BaseModel):
    public_token: str

class AnalyticsResponse(BaseModel):
    income_summary: dict
    expense_summary: dict
    cash_flow: dict
    balance_trend: dict
    top_merchants: List[dict]
    category_breakdown: dict

class FinancialOverview(BaseModel):
    income_tracking: Dict[str, List[Dict[str, Union[float, str, date]]]]
    expense_tracking: Dict[str, Union[float, List[Tuple[str, float]]]]
    balance_overview: Dict[str, float]
    budgeting: Dict[str, Union[float, int]]
    financial_planning: Dict[str, Union[float, List[str]]]
    calendar_visualization: List[Dict[str, Union[str, List[Dict[str, Union[float, str]]]]]]

@app.post("/create_link_token")
async def create_link_token():
    try:
        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Your App Name",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id="unique_user_id")
        )
        response = client.link_token_create(request)
        return {"link_token": response['link_token']}
    except plaid.ApiException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exchange_public_token")
async def exchange_public_token(public_token: PublicToken):
    try:
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token.public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        # In a real application, you would securely store this access_token
        return {"access_token": access_token}
    except plaid.ApiException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get_analytics/{access_token}")
async def get_analytics(access_token: str):
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)  # Get last 30 days of data

        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                include_personal_finance_category=True
            )
        )
        response = client.transactions_get(request)
        transactions = response['transactions']
        accounts = response['accounts']

        # Process transactions and accounts to generate analytics
        analytics = process_transactions(transactions, accounts)
        
        return analytics
    except plaid.ApiException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/create_sandbox_public_token")
async def create_sandbox_public_token():
    try:
        request = SandboxPublicTokenCreateRequest(
            institution_id="ins_109508",
            initial_products=[Products("transactions")]
        )
        response = client.sandbox_public_token_create(request)
        return {"public_token": response['public_token']}
    except plaid.ApiException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/financial_overview/{access_token}")
async def get_financial_overview(access_token: str):
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)  # Get last 90 days of data

        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                include_personal_finance_category=True
            )
        )
        response = client.transactions_get(request)
        transactions = response['transactions']
        accounts = response['accounts']

        overview = process_financial_data(transactions, accounts)
        return overview
    except plaid.ApiException as e:
        raise HTTPException(status_code=400, detail=str(e))

def process_transactions(transactions, accounts):
    # This is a simplified version. In a real application, you'd want more robust processing.
    total_income = sum(t['amount'] for t in transactions if t['amount'] > 0)
    total_expenses = sum(t['amount'] for t in transactions if t['amount'] < 0)
    
    category_spending = {}
    merchant_spending = {}
    for t in transactions:
        if t['amount'] < 0:  # it's an expense
            category = t['personal_finance_category']['primary']
            category_spending[category] = category_spending.get(category, 0) + abs(t['amount'])
            merchant = t['merchant_name'] or 'Unknown'
            merchant_spending[merchant] = merchant_spending.get(merchant, 0) + abs(t['amount'])

    return AnalyticsResponse(
        income_summary={"total": total_income},
        expense_summary={"total": abs(total_expenses)},
        cash_flow={"net": total_income - abs(total_expenses)},
        balance_trend={a['name']: a['balances']['current'] for a in accounts},
        top_merchants=sorted(
            [{"name": k, "amount": v} for k, v in merchant_spending.items()],
            key=lambda x: x['amount'],
            reverse=True
        )[:5],
        category_breakdown=category_spending
    )

def process_financial_data(transactions, accounts):
    # Income Tracking
    income = [t for t in transactions if t['amount'] > 0]
    income_tracking = {
        "recorded_income": [
            {"amount": t['amount'], "date": t['date'], "name": t['name']}
            for t in income
        ],
        "expected_income": predict_future_income(income)
    }

    # Expense Tracking
    expenses = [t for t in transactions if t['amount'] < 0]
    total_expenses = sum(abs(t['amount']) for t in expenses)
    expense_categories = {}
    for t in expenses:
        category = t['personal_finance_category']['primary']
        expense_categories[category] = expense_categories.get(category, 0) + abs(t['amount'])
    
    expense_tracking = {
        "total_monthly_expenses": total_expenses / 3 if expenses else 0,  # Assuming 90 days of data
        "top_spending_categories": sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)[:5] if expense_categories else [],
        "expense_trend": calculate_expense_trend(expenses)
    }

    # Balance Overview
    current_balance = sum(a['balances']['current'] for a in accounts)
    avg_daily_balance = calculate_average_daily_balance(transactions, accounts)
    
    balance_overview = {
        "current_balance": current_balance,
        "average_daily_balance": avg_daily_balance
    }

    # Budgeting (placeholder - would need user input for goals)
    budgeting = {
        "monthly_budget": 5000,  # placeholder value
        "progress": (5000 - expense_tracking["total_monthly_expenses"]) / 5000
    }

    # Financial Planning (placeholder - would need user input for goals)
    financial_planning = create_financial_plan(income_tracking, expense_tracking, balance_overview)

    # Calendar Visualization
    calendar_data = create_calendar_visualization(transactions)

    return FinancialOverview(
        income_tracking=income_tracking,
        expense_tracking=expense_tracking,
        balance_overview=balance_overview,
        budgeting=budgeting,
        financial_planning=financial_planning,
        calendar_visualization=calendar_data
    )

def predict_future_income(income):
    if not income:
        return []
    avg_income = sum(t['amount'] for t in income) / len(income)
    last_income_date = income[-1]['date']
    next_income_date = last_income_date + timedelta(days=30)  # Assuming monthly income
    return [{"amount": avg_income, "date": next_income_date}]

def calculate_expense_trend(expenses):
    # Group expenses by month and calculate total for each month
    monthly_expenses = {}
    for t in expenses:
        month = t['date'].strftime("%Y-%m")  # Format date as YYYY-MM string
        monthly_expenses[month] = monthly_expenses.get(month, 0) + abs(t['amount'])
    return sorted(monthly_expenses.items())

def calculate_average_daily_balance(transactions, accounts):
    # Simplified calculation - in reality, you'd need to consider the exact timing of transactions
    start_balance = sum(a['balances']['current'] for a in accounts) + sum(t['amount'] for t in transactions)
    end_balance = sum(a['balances']['current'] for a in accounts)
    return (start_balance + end_balance) / 2

def create_financial_plan(income_tracking, expense_tracking, balance_overview):
    # Placeholder function - in a real app, this would be much more sophisticated
    monthly_income = sum(t['amount'] for t in income_tracking['recorded_income']) / 3  # Assuming 90 days of data
    monthly_expenses = expense_tracking['total_monthly_expenses']
    savings_rate = (monthly_income - monthly_expenses) / monthly_income if monthly_income > 0 else 0
    
    return {
        "monthly_savings_goal": monthly_income * 0.2,
        "current_savings_rate": savings_rate,
        "recommendations": [
            "Try to save 20% of your income each month",
            "Focus on reducing expenses in your top spending category",
            "Build an emergency fund of 3-6 months of expenses"
        ]
    }

def create_calendar_visualization(transactions):
    calendar_data = {}
    for t in transactions:
        date_str = t['date'].isoformat()
        if date_str not in calendar_data:
            calendar_data[date_str] = []
        calendar_data[date_str].append({
            "amount": t['amount'],
            "name": t['name'],
            "category": t['personal_finance_category']['primary']
        })
    
    return [{"date": k, "transactions": v} for k, v in calendar_data.items()]

MX_BASE_URL = "https://int-api.mx.com"  # Development environment URL
MX_CLIENT_ID = os.getenv('MX_CLIENT_ID')
MX_API_KEY = os.getenv('MX_API_KEY')
MX_BASIC_AUTH_VALUE = os.getenv('MX_BASIC_AUTH_VALUE')

def mx_headers():
    return {
        "Accept": "application/vnd.mx.api.v1+json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {MX_BASIC_AUTH_VALUE}"
    }

@app.get("/mx_transactions/{user_guid}")
async def get_mx_transactions(user_guid: str):
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=180)  # Get last 6 months of data

        url = f"{MX_BASE_URL}/users/{user_guid}/transactions"
        params = {
            "from_date": start_date.isoformat(),
            "to_date": end_date.isoformat(),
            "page": 1,
            "records_per_page": 500  # Adjust as needed
        }

        transactions = []
        while True:
            response = requests.get(url, headers=mx_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            transactions.extend(data['transactions'])
            
            if data['pagination']['current_page'] >= data['pagination']['total_pages']:
                break
            
            params['page'] += 1

        return {"transactions": transactions}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

class MXUser(BaseModel):
    email: str
    id: str
    is_disabled: bool = False
    metadata: str = ""

@app.post("/create_mx_user")
async def create_mx_user(user: MXUser):
    try:
        url = f"{MX_BASE_URL}/users"
        payload = {
            "user": user.dict()
        }
        headers = mx_headers()
        print(f"Headers: {headers}")  # Debug print
        response = requests.post(url, headers=headers, json=payload)
        print(f"Response status: {response.status_code}")  # Debug print
        print(f"Response content: {response.text}")  # Debug print
        response.raise_for_status()
        data = response.json()
        return {"user_guid": data['user']['guid']}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

class MXMember(BaseModel):
    user_guid: str
    institution_code: str
    credentials: dict

@app.post("/connect_mx_bank")
async def connect_mx_bank(member: MXMember, background_tasks: BackgroundTasks):
    try:
        # Step 1: Create a member (connection to a financial institution)
        url = f"{MX_BASE_URL}/users/{member.user_guid}/members"
        payload = {
            "member": {
                "institution_code": member.institution_code,
                "credentials": member.credentials
            }
        }
        response = requests.post(url, headers=mx_headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        member_guid = data['member']['guid']

        # Step 2: Aggregate the member's accounts (this is an asynchronous process)
        url = f"{MX_BASE_URL}/users/{member.user_guid}/members/{member_guid}/aggregate"
        response = requests.post(url, headers=mx_headers())
        response.raise_for_status()

        # Step 3: Start a background task to check aggregation status
        background_tasks.add_task(check_aggregation_status, member.user_guid, member_guid)

        return {"message": "Bank connection initiated. Aggregation in progress."}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

async def check_aggregation_status(user_guid: str, member_guid: str):
    url = f"{MX_BASE_URL}/users/{user_guid}/members/{member_guid}/status"
    max_attempts = 10
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(url, headers=mx_headers())
            response.raise_for_status()
            data = response.json()
            status = data['member']['connection_status']

            if status == 'CONNECTED':
                print(f"Member {member_guid} successfully aggregated.")
                return
            elif status in ['FAILED', 'DENIED', 'PREVENTED', 'REJECTED', 'EXPIRED']:
                print(f"Aggregation failed for member {member_guid}. Status: {status}")
                return

            time.sleep(5)  # Wait for 5 seconds before checking again
            attempt += 1
        except requests.RequestException as e:
            print(f"Error checking aggregation status: {str(e)}")
            return

    print(f"Aggregation status check timed out for member {member_guid}")

@app.get("/mx_institutions")
async def get_mx_institutions(
    name: str = Query(None, description="List only institutions in which the appended string appears."),
    page: int = Query(1, description="Specify current page."),
    records_per_page: int = Query(25, ge=10, le=100, description="Number of records per page. Range: 10-100."),
    supports_account_identification: bool = Query(None, description="Filter institutions supporting account identification."),
    supports_account_statement: bool = Query(None, description="Filter institutions supporting account statements."),
    supports_account_verification: bool = Query(None, description="Filter institutions supporting account verification."),
    supports_transaction_history: bool = Query(None, description="Filter institutions supporting extended transaction history.")
):
    try:
        url = f"{MX_BASE_URL}/institutions"
        params = {
            "page": page,
            "records_per_page": records_per_page
        }
        
        # Add optional parameters if they are provided
        if name:
            params["name"] = name
        if supports_account_identification is not None:
            params["supports_account_identification"] = supports_account_identification
        if supports_account_statement is not None:
            params["supports_account_statement"] = supports_account_statement
        if supports_account_verification is not None:
            params["supports_account_verification"] = supports_account_verification
        if supports_transaction_history is not None:
            params["supports_transaction_history"] = supports_transaction_history

        response = requests.get(url, headers=mx_headers(), params=params)
        print(f"Request URL: {response.url}")  # Debug print
        print(f"Response status code: {response.status_code}")  # Debug print
        print(f"Response headers: {response.headers}")  # Debug print
        print(f"Response content: {response.text[:1000]}")  # Print first 1000 characters for debugging

        response.raise_for_status()
        data = response.json()
        
        institutions = data.get('institutions', [])
        
        return {
            "institutions": [
                {
                    "name": inst['name'],
                    "institution_code": inst['code'],
                    "medium_logo_url": inst['medium_logo_url']
                }
                for inst in institutions
            ],
            "pagination": data.get('pagination', {}),
            "total_institutions": len(institutions)
        }
    except requests.RequestException as e:
        print(f"Error: {str(e)}")  # Debug print
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error response content: {e.response.text}")  # Debug print
        raise HTTPException(status_code=400, detail=str(e))