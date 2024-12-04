import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.sqlite import insert
import concurrent.futures
from ..models.exchange_rate import ExchangeRate, Base
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExchangeRateScraper:
    """
    Scraper for fetching and storing exchange rate data from Yahoo Finance
    """
    
    def __init__(self, db_path='exchange_rates.db'):
        """
        Initialize the scraper with database connection
        
        Args:
            db_path (str): Path to SQLite database file
        """
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'timeout': 30},  # Increase SQLite timeout
            pool_size=1,                   # Single connection pool for SQLite
            max_overflow=0                 # No overflow connections
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_exchange_data(self, quote: str, from_date: str, to_date: str) -> str:
        """
        Fetch exchange rate data with pagination for long periods
        
        Args:
            quote: Currency pair (e.g., 'GBPINR=X')
            from_date: Start timestamp
            to_date: End timestamp
        
        Returns:
            str: Combined HTML content from all chunks
        """
        from_date = int(from_date)
        to_date = int(to_date)
        
        logger.info(
            f"Fetching data for {quote} from "
            f"{datetime.fromtimestamp(from_date).strftime('%Y-%m-%d')} to "
            f"{datetime.fromtimestamp(to_date).strftime('%Y-%m-%d')}"
        )
        
        # Split request into 3-month chunks
        three_months = 90 * 24 * 60 * 60  # in seconds
        chunks = []
        current_from = from_date
        
        while current_from < to_date:
            current_to = min(current_from + three_months, to_date)
            chunks.append((str(current_from), str(current_to)))
            current_from = current_to + 1
        
        logger.info(f"Split request into {len(chunks)} chunks")
        
        # Fetch chunks in parallel
        all_data = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(
                    self._fetch_and_save_chunk,
                    quote,
                    chunk_from,
                    chunk_to,
                    i+1,
                    len(chunks)
                ): (chunk_from, chunk_to)
                for i, (chunk_from, chunk_to) in enumerate(chunks)
            }
            
            for future in concurrent.futures.as_completed(futures):
                chunk_from, chunk_to = futures[future]
                try:
                    data = future.result()
                    if data:
                        all_data.append(data)
                except Exception as exc:
                    logger.error(f"Chunk {chunk_from} to {chunk_to} failed: {exc}")
        
        return '\n'.join(all_data) if all_data else None

    def _fetch_and_save_chunk(self, quote: str, chunk_from: str, 
                             chunk_to: str, chunk_index: int, 
                             total_chunks: int) -> str:
        """
        Fetch and save a single chunk of exchange rate data
        """
        logger.info(f"Fetching chunk {chunk_index}/{total_chunks}")
        chunk_data = self._fetch_chunk(quote, chunk_from, chunk_to)
        
        if chunk_data:
            parsed_data = self.parse_exchange_data(chunk_data, quote)
            if parsed_data:
                logger.info(f"Saving {len(parsed_data)} records from chunk {chunk_index}")
                self.save_to_database(parsed_data)
                
        return chunk_data

    @lru_cache(maxsize=32)
    def _fetch_chunk(self, quote: str, from_date: str, to_date: str) -> str:
        """
        Cached method to fetch a chunk of data
        """
        try:
            return self._fetch_data_with_retry(quote, from_date, to_date)
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return None

    def _fetch_data_with_retry(self, quote: str, from_date: str, 
                              to_date: str, max_retries: int = 3) -> str:
        """
        Fetch data with retry logic
        """
        for attempt in range(max_retries):
            try:
                ua = UserAgent()
                headers = {'User-Agent': ua.random}
                
                url = (
                    f"https://finance.yahoo.com/quote/{quote}/history"
                    f"?period1={from_date}&period2={to_date}&interval=1d"
                )
                
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    return response.text
                    
                logger.error(f"Failed to fetch data: Status {response.status_code}")
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # Exponential backoff
                time.sleep(2 ** attempt)
        
        return None

    def parse_exchange_data(self, html_content: str, currency_pair: str) -> list:
        """
        Parse exchange rate data from HTML content
        
        Returns:
            list: List of dictionaries containing exchange rate data
        """
        if not html_content:
            logger.error("Empty HTML content received")
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr', class_='yf-j5d1ld')
        
        if not rows:
            logger.error("No exchange rate rows found in HTML content")
            return None
        
        data = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:
                try:
                    date_str = cols[0].text.strip()
                    if not date_str:
                        continue
                        
                    date = datetime.strptime(date_str, '%b %d, %Y').strftime('%Y-%m-%d')
                    
                    # Validate data
                    if any(col.text.strip() in ['-', '', 'null', 'None'] 
                          for col in cols[1:6]):
                        logger.warning(f"Invalid data for date: {date}")
                        continue
                        
                    exchange_rate_data = {
                        'currency_pair': currency_pair,
                        'date': date,
                        'open_rate': float(cols[1].text.replace(',', '')),
                        'high_rate': float(cols[2].text.replace(',', '')),
                        'low_rate': float(cols[3].text.replace(',', '')),
                        'close_rate': float(cols[4].text.replace(',', '')),
                        'adj_close': float(cols[5].text.replace(',', '')),
                        'volume': int(cols[6].text.replace(',', '')) 
                                 if cols[6].text.strip() != '-' else 0
                    }
                    data.append(exchange_rate_data)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue
        
        if not data:
            logger.error("No valid data rows were parsed")
            return None
            
        logger.info(f"Successfully parsed {len(data)} rows")
        return data

    def save_to_database(self, exchange_rates: list) -> None:
        """
        Save exchange rates to database with conflict resolution
        """
        if not exchange_rates:
            return
        
        session = self.Session()
        try:
            for rate_data in exchange_rates:
                stmt = insert(ExchangeRate).values(**rate_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['currency_pair', 'date'],
                    set_=rate_data
                )
                session.execute(stmt)
            session.commit()
            logger.info(f"Saved {len(exchange_rates)} records to database")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            session.rollback()
            raise
            
        finally:
            session.close()