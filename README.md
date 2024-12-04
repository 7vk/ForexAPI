# Forex Exchange Rate API

A Flask-based REST API for fetching and managing foreign exchange rates.

## Features
- Real-time exchange rate data scraping
- Historical exchange rate data
- Support for multiple currency pairs
- Configurable time periods (1W, 1M, 3M, 6M, 1Y)

## Setup
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure environment variables
5. Run the application:
   ```bash
   python run.py
   ```

## API Endpoints
- `POST /api/forex-data`: Get exchange rate data
- `GET /api/sync-forex-data`: Sync exchange rate data

## Deployment
This application is configured for deployment on Railway.app. 