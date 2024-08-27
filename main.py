import os
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
from typing import List

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)