import requests
from bs4 import BeautifulSoup
import json
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

load_dotenv(override=True)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)

# senator-transactions table structure
# id: bigint
# owner: string
# ticker: string
# asset_name: string
# transaction_type: string
# transaction_date: date
# amount: string
def save_transaction(transaction):
    try:
        # Standardize transaction type
        transaction_type = transaction['transaction_type'].lower()
        if 'purchase' in transaction_type or 'buy' in transaction_type:
            transaction['transaction_type'] = 'buy'
        elif 'sale' in transaction_type or 'sell' in transaction_type:
            transaction['transaction_type'] = 'sell'
            
        # Check if transaction already exists
        existing = supabase.table("senator-transactions").select("*").eq("owner", transaction['owner']).eq("ticker", transaction['ticker']).eq("transaction_date", transaction['transaction_date']).eq("amount", transaction['amount']).execute()
        
        if existing.data and len(existing.data) > 0:
            print(f"Skipping duplicate transaction for {transaction['owner']} - {transaction['ticker']}")
            return
            
        # If no duplicate found, insert the transaction
        supabase.table("senator-transactions").insert(transaction).execute()
        print(f"Saved transaction for {transaction['owner']} - {transaction['ticker']}")
    except Exception as e:
        print(f"Error saving transaction: {e}")

def fetch_disclosures(start, length):
    url = "https://investassist.app/api/senator-trading"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Calculate date range for past 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months ago
    
    # Format dates as required by the API (MM/DD/YYYY HH:MM:SS)
    date_start = start_date.strftime("%m/%d/%Y %H:%M:%S")
    date_end = end_date.strftime("%m/%d/%Y %H:%M:%S")
    
    body = {
        "draw": 1,
        "start": start,
        "length": length,
        "dateStart": date_start,
        "dateEnd": date_end
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching disclosures: {e}")
        return None

def fetch_senate_disclosure(report_id):
    url = f"https://efdsearch.senate.gov/search/view/annual/{report_id}/"

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Cookie": "s_tslv=1745059014204; s_nr30=1745059014205-New; AMCV_345E01D16312552B0A495FAC%40AdobeOrg=179643557%7CMCIDTS%7C20198%7CMCMID%7C62025720127003172851280363150845915312%7CMCAAMLH-1745663814%7C7%7CMCAAMB-1745663814%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1745066214s%7CNONE%7CvVersion%7C5.5.0; csrftoken=Bqa8kdUjngywHWcCwC2JHU0xlLhBQ8LH; sessionid=gAWVGAAAAAAAAAB9lIwQc2VhcmNoX2FncmVlbWVudJSIcy4:1u6gYE:MkLDnb0nq1cWdioVbC5NrYy-Er3fEB4akx8X21m_DCg; 33a5c6d97f299a223cb6fc3925909ef7=07ea87aed6353e55690814fa725e7352",
        "DNT": "1",
        "Host": "efdsearch.senate.gov",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        print(f"Request failed with status code {response.status_code}")
        return None

def parse_senate_disclosure(html_content):
    if not html_content:
        print("No HTML content received")
        return None
    
    print("Starting to parse HTML content...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize the data structure
    data = {
        'transactions': []
    }
    
    # Helper function to clean text
    def clean_text(text):
        if text:
            return ' '.join(text.strip().split())
        return None

    # Helper function to extract table data
    def extract_table_data(table):
        if not table:
            print("No table found")
            return []
        
        print("\nProcessing transactions table")
        rows = table.find_all('tr')[1:]  # Skip header row
        print(f"Found {len(rows)} rows in table")
        items = []
        
        # Get headers first
        headers = []
        header_row = table.find('tr', {'class': 'header'})
        if header_row:
            headers = [clean_text(th.text) for th in header_row.find_all('th')]
            print(f"Found headers: {headers}")
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:  # Ensure we have at least some data
                item = {}
                for i, col in enumerate(cols):
                    if i < len(headers) and headers[i]:  # Only process if we have a valid header
                        key = headers[i].lower().replace(' ', '_').replace('#', 'number').replace('/', '_')
                        value = clean_text(col.text)
                        if value and value != 'n/a':
                            item[key] = value
                
                if item:  # Only add if we found some data
                    items.append(item)
        
        print(f"Extracted {len(items)} transactions")
        return items

    # Find transactions section
    print("\nLooking for transactions section...")
    section = soup.find('h3', string=lambda text: text and 'Part 4b. Transactions' in text) or \
             soup.find('h4', string=lambda text: text and 'Part 4b. Transactions' in text)
    
    if section:
        print("Found transactions section")
        # Try multiple ways to find the table
        table = None
        
        # Method 1: Look for table directly after the section
        table = section.find_next('table')
        
        # Method 2: Look for table in parent's children
        if not table:
            parent = section.find_parent()
            if parent:
                table = parent.find('table')
        
        # Method 3: Look for table in table-responsive div
        if not table:
            table_div = section.find_next('div', {'class': 'table-responsive'})
            if table_div:
                table = table_div.find('table')
        
        # Method 4: Look for any table with transaction-related headers
        if not table:
            tables = soup.find_all('table')
            for t in tables:
                headers = t.find_all('th')
                header_texts = [h.text.strip().lower() for h in headers]
                if any('incurred' in text or 'type' in text or 'amount' in text for text in header_texts):
                    table = t
                    break
        
        if table:
            data['transactions'] = extract_table_data(table)
        else:
            print("No transactions table found")
    else:
        print("No transactions section found")

    return data

def process_disclosure(disclosure):
    """Process a single disclosure and save its transactions to Supabase"""
    report_id = disclosure['reportLink'].split('/')[-2]  # Extract report ID from URL
    html_content = fetch_senate_disclosure(report_id)
    
    if not html_content:
        print(f"Failed to fetch disclosure for {disclosure['filerName']}")
        return
    
    parsed_data = parse_senate_disclosure(html_content)
    if not parsed_data or not parsed_data.get('transactions'):
        print(f"No transactions found for {disclosure['filerName']}")
        return
    
    # Process each transaction
    for transaction in parsed_data['transactions']:
        try:
            print(f"\nFound transaction in HTML:")
            print(json.dumps(transaction, indent=2))
            
            # Extract date and convert to proper format
            date_str = transaction.get('transaction_date', '')
            if not date_str:
                print(f"Skipping transaction with no date for {disclosure['filerName']}")
                continue
                
            # Try different date formats
            formatted_date = None
            date_formats = [
                '%m/%d/%Y',  # MM/DD/YYYY
                '%Y',        # YYYY
                '%m/%Y',     # MM/YYYY
                '%Y-%m-%d',  # YYYY-MM-DD
                '%d/%m/%Y'   # DD/MM/YYYY
            ]
            
            for date_format in date_formats:
                try:
                    date_obj = datetime.strptime(date_str.strip(), date_format)
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
            
            if not formatted_date:
                print(f"Could not parse date: {date_str} for {disclosure['filerName']}")
                continue

            # Extract asset name and ticker
            asset_name = transaction.get('asset_name', '')
            ticker = transaction.get('ticker', '')
            
            # Extract transaction type and clean it
            transaction_type = transaction.get('transaction_type', '').strip()
            
            # Extract and clean amount - ensure it's a string
            amount = transaction.get('amount', '').strip()
            if amount:
                # Remove any currency symbols and clean up the amount
                amount = amount.replace('$', '').replace(',', '').strip()
            
            # Convert transaction data to match our table structure
            db_transaction = {
                'owner': str(disclosure['filerName']),  # text
                'ticker': str(ticker),                  # text
                'asset_name': str(asset_name),          # text
                'transaction_type': str(transaction_type),  # text
                'transaction_date': formatted_date,     # date
                'amount': str(amount)                   # text
            }
            
            print("\nProcessed transaction data:")
            print(json.dumps(db_transaction, indent=2))
            
            # Check which required fields are missing
            missing_fields = []
            if not db_transaction['transaction_date']:
                missing_fields.append('transaction_date')
            if not db_transaction['amount']:
                missing_fields.append('amount')
            if not db_transaction['asset_name']:
                missing_fields.append('asset_name')
            if not db_transaction['owner']:
                missing_fields.append('owner')
            
            if missing_fields:
                print(f"Skipping transaction for {disclosure['filerName']} - Missing fields: {', '.join(missing_fields)}")
                continue
                
            save_transaction(db_transaction)
            print(f"Saved transaction: {db_transaction['owner']} - {db_transaction['asset_name']} ({db_transaction['ticker']}) - {db_transaction['transaction_type']} - {db_transaction['amount']} on {db_transaction['transaction_date']}")
                
        except Exception as e:
            print(f"Error processing transaction for {disclosure['filerName']}: {e}")
            continue

def process_all_disclosures(start=0, length=100):
    """Process all disclosures in batches"""
    while True:
        print(f"\nFetching disclosures batch starting at {start}")
        disclosures = fetch_disclosures(start, length)
        
        if not disclosures or not disclosures.get('data'):
            print("No more disclosures to process")
            break
            
        print(f"Processing {len(disclosures['data'])} disclosures")
        for disclosure in disclosures['data']:
            print(f"\nProcessing disclosure for {disclosure['filerName']}")
            process_disclosure(disclosure)
            time.sleep(2)  # Increased delay to avoid overwhelming the server
        
        start += length
        if start >= disclosures.get('recordsTotal', 0):
            break

if __name__ == "__main__":
    process_all_disclosures()