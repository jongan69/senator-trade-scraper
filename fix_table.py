import requests
from bs4 import BeautifulSoup
import json
import os
from supabase import create_client, Client
from datetime import datetime
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

# First, let's analyze all unique transaction types
print("Analyzing transaction types...")
page_size = 1000
offset = 0
unique_types = set()

while True:
    transactions = supabase.table("senator-transactions").select("transaction_type").range(offset, offset + page_size - 1).execute()
    
    if not transactions.data:
        break
        
    for transaction in transactions.data:
        unique_types.add(transaction['transaction_type'])
    
    offset += page_size

print("\nFound the following transaction types:")
for t in sorted(unique_types):
    print(f"- {t}")

# Now process the updates
print("\nStarting updates...")
page_size = 1000
offset = 0
total_updated = 0

while True:
    transactions = supabase.table("senator-transactions").select("*").range(offset, offset + page_size - 1).execute()
    
    if not transactions.data:
        break
        
    # Process each transaction and update the transaction type
    for transaction in transactions.data:
        current_type = transaction['transaction_type']
        new_type = None
        
        if current_type in ['Sale (Full)', 'Sale (Partial)', 'Sale']:
            new_type = 'sell'
        elif current_type in ['Purchase', 'Buy']:
            new_type = 'buy'
        
        if new_type:
            # Update the transaction type in the database
            supabase.table("senator-transactions").update({
                "transaction_type": new_type
            }).eq("id", transaction['id']).execute()
            
            total_updated += 1
            if total_updated % 100 == 0:  # Print progress every 100 updates
                print(f"Updated {total_updated} transactions so far...")
    
    offset += page_size

print(f"\nTransaction type updates completed! Total transactions updated: {total_updated}")


