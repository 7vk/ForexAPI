# Forex Exchange Rate API

A Flask-based REST API for fetching and managing foreign exchange rates.

## Features
- Exchange rate data scraping
- Historical exchange rate data
- Support for multiple currency pairs
- Configurable time periods (1W, 1M, 3M, 6M, 1Y)

## Setup Instructions

Follow these steps to set up the Forex Exchange Rate API on your local machine:

1. **Clone the Repository**:

2. **Create a Virtual Environment**:
   - **Linux/MacOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows**:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```

3. **Install Dependencies**:
   Ensure you have `pip` installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - Open the `.env` file and configure the necessary environment variables, such as `DATABASE_URL`, `API_KEYS`, etc.

5. **Initialize the Database**:
   - Run the following command to create the necessary database tables:
     ```bash
     python -c "from backend.app.models.exchange_rate import Base; from sqlalchemy import create_engine; engine = create_engine('sqlite:///exchange_rates.db'); Base.metadata.create_all(engine)"
     ```

## Running the Application

Once the setup is complete, you can run the application using the following steps:

1. **Activate the Virtual Environment**:
   - **Linux/MacOS**:
     ```bash
     source venv/bin/activate
     ```
   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```

2. **Start the Flask Application**:
   - Run the application using:
     ```bash
     python run.py
     ```
   - The application will start on `http://localhost:5000` by default.

3. **Access the API**:
   - You can test the API endpoints using tools like `curl`, Postman, or directly from your browser for GET requests.

## API Endpoints
- `POST /api/forex-data`: Get exchange rate data
- `GET /api/sync-forex-data`: Sync exchange rate data

## Postman Documentation

For detailed API documentation and examples, visit the [Postman Documentation](https://documenter.getpostman.com/view/38132779/2sAYBaAVBC).

## Cron Job Integration

The `/api/sync-forex-data` endpoint is implemented through a CRON job using [cron-job.org](https://cron-job.org). This ensures that the synchronization of forex data occurs automatically at scheduled intervals, keeping the database updated with the latest exchange rates.

## Deployment
This application is configured for deployment on Railway.app.  LINK - [https://web-production-88ce.up.railway.app/api/sync-forex-data](https://web-production-88ce.up.railway.app/api/sync-forex-data)
