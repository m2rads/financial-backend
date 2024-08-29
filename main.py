import os
import certifi
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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
    income_tracking: Dict[str, List[Dict[str, Union[float, str]]]]
    expense_tracking: Dict[str, Union[float, List[Tuple[str, float]], List[Tuple[str, float]]]]
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
        "total_monthly_expenses": total_expenses / 3,  # Assuming 90 days of data
        "top_spending_categories": sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)[:5],
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
    # Simple prediction based on average income and frequency
    if not income:
        return []
    avg_income = sum(t['amount'] for t in income) / len(income)
    last_income_date = datetime.strptime(income[-1]['date'], "%Y-%m-%d")
    next_income_date = last_income_date + timedelta(days=30)  # Assuming monthly income
    return [{"amount": avg_income, "date": next_income_date.strftime("%Y-%m-%d")}]

def calculate_expense_trend(expenses):
    # Group expenses by month and calculate total for each month
    monthly_expenses = {}
    for t in expenses:
        month = t['date'][:7]  # YYYY-MM
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
    # Group transactions by date
    calendar_data = {}
    for t in transactions:
        date = t['date']
        if date not in calendar_data:
            calendar_data[date] = []
        calendar_data[date].append({
            "amount": t['amount'],
            "name": t['name'],
            "category": t['personal_finance_category']['primary']
        })
    
    # Convert to list of dicts for easier frontend processing
    return [{"date": k, "transactions": v} for k, v in calendar_data.items()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)