import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import requests
from typing import Optional

# Load environment variables from .env file
load_dotenv('.env')

app = FastAPI(
    title="MX Platform API",
    description="FastAPI wrapper for MX Platform API",
    version="1.0.0",
)

BASE_URL = 'https://int-api.mx.com' if os.environ.get("DEVELOPMENT_ENVIRONMENT") != 'production' else 'https://api.mx.com'
AUTH = (os.environ.get("MX_CLIENT_ID"), os.environ.get("MX_API_KEY"))
HEADERS = {
    'Accept': 'application/vnd.mx.api.v1+json',
    'Authorization': f'Basic {os.environ.get("MX_BASIC_AUTH_VALUE")}'
}

def mx_request(method, endpoint, **kwargs):
    url = f"{BASE_URL}{endpoint}"
    response = requests.request(method, url, auth=AUTH, headers=HEADERS, **kwargs)
    response.raise_for_status()
    return response.json()

@app.get("/test", summary="Test API connection")
async def test():
    try:
        return mx_request('GET', '/users')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users", summary="Get all users")
async def get_users():
    try:
        return mx_request('GET', '/users')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/user/{guid}", summary="Delete a user")
async def delete_user(guid: str):
    try:
        mx_request('DELETE', f'/users/{guid}')
        return {"user_guid": guid}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/get_mxconnect_widget_url", summary="Get MX Connect widget URL")
async def get_mxconnect_widget_url(request: Request):
    try:
        data = await request.json()
        user_guid = data.get('user_guid')

        if user_guid is None:
            user_response = mx_request('POST', '/users', json={'user': {'metadata': ''}})
            user_guid = user_response['user']['guid']

        current_member_guid = data.get('current_member_guid')

        widget_payload = {
            'widget_url': {
                'widget_type': 'connect_widget',
                'is_mobile_webview': False,
                'mode': 'verification',
                'ui_message_version': 4,
                'include_transactions': True,
            }
        }

        if current_member_guid:
            widget_payload['widget_url']['current_member_guid'] = current_member_guid

        return mx_request('POST', f'/users/{user_guid}/widget_urls', json=widget_payload)
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_guid}/members/{member_guid}/verify", summary="Verify member")
async def verify(user_guid: str, member_guid: str):
    try:
        return mx_request('GET', f'/users/{user_guid}/members/{member_guid}/account_numbers')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_guid}/members/{member_guid}/identify", summary="Get account owners")
async def identify_get(user_guid: str, member_guid: str):
    try:
        return mx_request('GET', f'/users/{user_guid}/members/{member_guid}/account_owners')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/{user_guid}/members/{member_guid}/identify", summary="Identify member")
async def identify_post(user_guid: str, member_guid: str):
    try:
        return mx_request('POST', f'/users/{user_guid}/members/{member_guid}/identify')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_guid}/members/{member_guid}/check_balance", summary="Get user accounts")
async def balances_get(user_guid: str, member_guid: str):
    try:
        return mx_request('GET', f'/users/{user_guid}/accounts')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/{user_guid}/members/{member_guid}/check_balance", summary="Check balances")
async def balances_post(user_guid: str, member_guid: str):
    try:
        return mx_request('POST', f'/users/{user_guid}/members/{member_guid}/check_balance')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_guid}/members/{member_guid}/transactions", summary="Get transactions by member")
async def transactions(user_guid: str, member_guid: str):
    try:
        return mx_request('GET', f'/users/{user_guid}/members/{member_guid}/transactions')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_guid}/members/{member_guid}/status", summary="Check member status")
async def check_member_status(user_guid: str, member_guid: str):
    try:
        return mx_request('GET', f'/users/{user_guid}/members/{member_guid}/status')
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=0)
