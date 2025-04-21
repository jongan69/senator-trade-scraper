import os
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(override=True)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)

def find_duplicates():
    print("Finding duplicate transactions...")
    page_size = 1000
    offset = 0
    transaction_map = defaultdict(list)
    
    # First pass: collect all transactions and group them by their identifying characteristics
    while True:
        transactions = supabase.table("senator-transactions").select("*").range(offset, offset + page_size - 1).execute()
        
        if not transactions.data:
            break
            
        for transaction in transactions.data:
            # Create a unique key based on relevant fields
            key = (
                transaction['owner'],
                transaction['ticker'],
                transaction['transaction_type'],
                transaction['transaction_date'],
                transaction['amount']
            )
            transaction_map[key].append(transaction['id'])
        
        offset += page_size
    
    # Find duplicates (entries with more than one ID)
    duplicates = {key: ids for key, ids in transaction_map.items() if len(ids) > 1}
    
    return duplicates

def remove_duplicates(duplicates):
    print("\nRemoving duplicate transactions...")
    total_removed = 0
    
    for key, ids in duplicates.items():
        # Keep the first ID and delete the rest
        keep_id = ids[0]
        delete_ids = ids[1:]
        
        # Delete the duplicate records
        for delete_id in delete_ids:
            supabase.table("senator-transactions").delete().eq("id", delete_id).execute()
            total_removed += 1
            
        if total_removed % 100 == 0:
            print(f"Removed {total_removed} duplicate transactions so far...")
    
    return total_removed

def main():
    print("Starting duplicate removal process...")
    
    # Find duplicates
    duplicates = find_duplicates()
    
    if not duplicates:
        print("No duplicates found!")
        return
    
    print(f"\nFound {len(duplicates)} sets of duplicate transactions")
    
    # Remove duplicates
    total_removed = remove_duplicates(duplicates)
    
    print(f"\nDuplicate removal completed!")
    print(f"Total duplicate transactions removed: {total_removed}")

if __name__ == "__main__":
    main() 