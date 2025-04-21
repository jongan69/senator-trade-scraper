from datetime import datetime, timedelta
import requests

def fetch_house_disclosures():
    url = "https://investassist.app/api/house-rep-trading"
       
    # Get the current year
    current_year = datetime.now().year
    
    body = {
        "filingYear": str(current_year),
    }
    
    try:
        response = requests.post(url, json=body)
        response.raise_for_status()  # Raise an exception for bad status codes
        print(response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching disclosures: {e}")
        return None
    
if __name__ == "__main__":
    fetch_house_disclosures()