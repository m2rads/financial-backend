# Financial Analytics API

This is a FastAPI application that integrates with Plaid to provide financial analytics and insights.

## Prerequisites

- Python 3.7+
- pip (Python package installer)

## Setup

1. Clone the repository:
   ```
   git clone <your-repo-url>
   cd <your-repo-directory>
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the root directory and add your Plaid API credentials:
   ```
   PLAID_CLIENT_ID=your_client_id_here
   PLAID_SECRET=your_secret_here
   ```

## Running the Application

1. Make sure your virtual environment is activated.

2. Run the FastAPI application:
   ```
   python main.py
   ```

   The application will start and be available at `http://0.0.0.0:8000`.

## API Endpoints

- `POST /create_link_token`: Create a Plaid Link token
- `POST /exchange_public_token`: Exchange a public token for an access token
- `GET /get_analytics/{access_token}`: Get financial analytics
- `POST /create_sandbox_public_token`: Create a sandbox public token (for testing)
- `GET /financial_overview/{access_token}`: Get a comprehensive financial overview

## Testing the API

You can use tools like curl or Postman to test the API endpoints. Here's an example workflow:

1. Create a sandbox public token:
   ```
   curl -X POST http://0.0.0.0:8000/create_sandbox_public_token
   ```

2. Exchange the public token for an access token:
   ```
   curl -X POST http://0.0.0.0:8000/exchange_public_token -H "Content-Type: application/json" -d '{"public_token": "your_public_token_here"}'
   ```

3. Get financial overview:
   ```
   curl -X GET http://0.0.0.0:8000/financial_overview/your_access_token_here
   ```

## Documentation

Once the application is running, you can view the API documentation at:
- Swagger UI: `http://0.0.0.0:8000/docs`
- ReDoc: `http://0.0.0.0:8000/redoc`

## Note

This application uses Plaid's Sandbox environment. For production use, you would need to change the configuration and implement proper security measures.
