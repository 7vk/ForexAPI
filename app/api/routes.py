from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from ..models.exchange_rate import ExchangeRate
from ..services.scraper import ExchangeRateScraper
import logging
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import os

# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
database_url = os.getenv('DATABASE_URL', 'sqlite:///exchange_rates.db')
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)

def parse_period(period: str) -> timedelta:
    """
    Convert period string to timedelta object
    
    Args:
        period (str): Time period (e.g., '1W', '1M', '3M', '6M', '1Y')
    
    Returns:
        timedelta: Corresponding time period
    
    Raises:
        ValueError: If period format is invalid
    """
    period_mapping = {
        '1W': timedelta(weeks=1),
        '1M': timedelta(days=30),
        '3M': timedelta(days=90),
        '6M': timedelta(days=180),
        '1Y': timedelta(days=365)
    }
    
    normalized_period = period.upper()
    if normalized_period in period_mapping:
        return period_mapping[normalized_period]
    
    raise ValueError(
        f"Invalid period: {period}. Supported periods are 1W, 1M, 3M, 6M, 1Y"
    )

@app.route('/api/forex-data', methods=['POST'])
def get_forex_data():
    """
    Endpoint to fetch forex data for a specific currency pair and time period
    """
    try:
        # Extract request parameters
        from_currency = request.json.get('from', 'AED')
        to_currency = request.json.get('to', 'INR')
        period = request.json.get('period', '1W')
        amount = float(request.json.get('amount', 1.0))
        
        logger.info(f"Request received - {from_currency} to {to_currency}, period: {period}")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - parse_period(period)
        
        # Format currency pair for Yahoo Finance
        currency_pair = f"{from_currency}{to_currency}=X"
        
        # Query database
        with Session() as session:
            data = session.query(ExchangeRate).filter(
                ExchangeRate.currency_pair == currency_pair,
                ExchangeRate.date >= start_date.strftime('%Y-%m-%d'),
                ExchangeRate.date <= end_date.strftime('%Y-%m-%d')
            ).order_by(ExchangeRate.date.asc()).all()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data available for the specified period and currency pair'
                }), 404
            
            # Process results
            latest_rate = data[-1].close_rate
            converted_amount = amount * latest_rate if amount else None
            
            forex_data = [
                {'date': rate.date, 'rate': rate.close_rate} 
                for rate in data
            ]
            
            return jsonify({
                'success': True,
                'from': from_currency,
                'to': to_currency,
                'period': period,
                'data': forex_data,
                'current_rate': latest_rate,
                'converted_amount': converted_amount
            })
            
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/sync-forex-data', methods=['GET'])
def sync_forex_data():
    """
    Endpoint to synchronize forex data for all supported currency pairs
    """
    try:
        currency_pairs = [
            ('GBP', 'INR'),
            ('AED', 'INR')
        ]
        
        logger.info("Starting forex data sync")
        
        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(process_single_pair, from_curr, to_curr)
                for from_curr, to_curr in currency_pairs
            ]
            
            # Collect results
            results = {}
            for future in concurrent.futures.as_completed(futures):
                pair_results = future.result()
                if pair_results:
                    results.update(pair_results)
        
        logger.info("Forex data sync completed")
        return jsonify({
            'message': 'Sync completed',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Sync process failed: {str(e)}")
        return jsonify({
            'error': f'Sync process failed: {str(e)}'
        }), 500

def process_single_pair(from_currency: str, to_currency: str) -> dict:
    """
    Process and store exchange rate data for a single currency pair
    
    Args:
        from_currency (str): Source currency code
        to_currency (str): Target currency code
    
    Returns:
        dict: Processing results for each time period
    """
    try:
        currency_pair = f"{from_currency}{to_currency}=X"
        results = {currency_pair: {}}
        periods = ['1W', '1M', '3M', '6M', '1Y']
        
        # Calculate date range for 1 year
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        logger.info(f"Syncing {currency_pair} for 1Y period")
        
        # Fetch and parse data
        scraper = ExchangeRateScraper()
        html_content = scraper.get_exchange_data(
            currency_pair, 
            str(int(start_date.timestamp())),
            str(int(end_date.timestamp()))
        )
        
        if not html_content:
            return {
                currency_pair: {
                    period: {'status': 'error', 'message': 'Failed to fetch data'}
                    for period in periods
                }
            }
        
        exchange_rates = scraper.parse_exchange_data(html_content, currency_pair)
        if not exchange_rates:
            return {
                currency_pair: {
                    period: {'status': 'error', 'message': 'No data found'}
                    for period in periods
                }
            }
        
        # Save data and calculate results for each period
        scraper.save_to_database(exchange_rates)
        for period in periods:
            period_delta = parse_period(period)
            period_start = end_date - period_delta
            period_records = [
                rate for rate in exchange_rates 
                if datetime.strptime(rate['date'], '%Y-%m-%d') >= period_start
            ]
            
            results[currency_pair][period] = {
                'status': 'success',
                'records': len(period_records)
            }
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing {currency_pair}: {str(e)}")
        return {
            currency_pair: {
                period: {'status': 'error', 'message': str(e)}
                for period in periods
            }
        }

if __name__ == '__main__':
    app.run(debug=True)