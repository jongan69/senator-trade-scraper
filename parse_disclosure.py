import requests
from bs4 import BeautifulSoup
import json

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
    
    # Debug: Print the first part of the HTML to understand structure
    print("\nFirst 500 characters of HTML:")
    print(html_content[:500])
    
    # Debug: Print all section headers to understand structure
    print("\nAll section headers found:")
    sections = soup.find_all(['h1', 'h2', 'h3', 'h4'])
    for section in sections:
        print(f"Found section: {section.text.strip()}")
    
    # Initialize the data structure
    data = {
        'report_info': {},
        'earned_income': [],
        'assets': [],
        'transactions': [],
        'gifts': [],
        'liabilities': [],
        'positions': [],
        'agreements': []
    }
    
    # Extract report information
    print("\nLooking for report info...")
    # Try different ways to find report info
    report_info = soup.find('div', {'class': 'report-info'}) or \
                 soup.find('div', string=lambda t: t and 'Report Type' in t) or \
                 soup.find('div', string=lambda t: t and 'Filing Date' in t)
    
    if report_info:
        print("Found report info section")
        data['report_info'] = {
            'filing_date': report_info.find('div', string='Filing Date').find_next('div').text.strip() if report_info.find('div', string='Filing Date') else None,
            'report_type': report_info.find('div', string='Report Type').find_next('div').text.strip() if report_info.find('div', string='Report Type') else None,
            'reporting_period': report_info.find('div', string='Reporting Period').find_next('div').text.strip() if report_info.find('div', string='Reporting Period') else None,
        }
    else:
        print("No report info section found")

    # Helper function to clean text
    def clean_text(text):
        if text:
            return ' '.join(text.strip().split())
        return None

    # Helper function to extract table data
    def extract_table_data(table, section):
        if not table:
            print(f"No table found for section: {section}")
            return []
        
        print(f"\nProcessing table for section: {section}")
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
        
        print(f"Extracted {len(items)} items from {section} table")
        return items

    # Helper function to find section and its table
    def find_section_and_table(section_text):
        # Try different ways to find the section
        section = soup.find('section', string=lambda text: text and section_text in text) or \
                 soup.find('div', string=lambda text: text and section_text in text) or \
                 soup.find('h3', string=lambda text: text and section_text in text) or \
                 soup.find('h4', string=lambda text: text and section_text in text)
        
        if section:
            # Try to find the table in different ways
            table = section.find_next('table') or \
                   section.find_parent().find('table') or \
                   section.find_next('div', {'class': 'table-responsive'}).find('table')
            return section, table
        return None, None

    # Extract earned income (Part 2)
    print("\nLooking for earned income section...")
    section, table = find_section_and_table('Part 2. Earned and Non-Investment Income')
    if section and table:
        print("Found earned income section")
        data['earned_income'] = extract_table_data(table, 'earned_income')
    else:
        print("No earned income section found")

    # Extract assets (Part 3)
    print("\nLooking for assets section...")
    section, table = find_section_and_table('Part 3. Assets')
    if section and table:
        print("Found assets section")
        data['assets'] = extract_table_data(table, 'assets')
    else:
        print("No assets section found")

    # Extract transactions (Part 4b)
    print("\nLooking for transactions section...")
    section, table = find_section_and_table('Part 4b. Transactions')
    if section and table:
        print("Found transactions section")
        data['transactions'] = extract_table_data(table, 'transactions')
    else:
        print("No transactions section found")

    # Extract gifts (Part 5)
    print("\nLooking for gifts section...")
    section, table = find_section_and_table('Part 5. Gifts')
    if section and table:
        print("Found gifts section")
        data['gifts'] = extract_table_data(table, 'gifts')
    else:
        print("No gifts section found")

    # Extract liabilities (Part 7)
    print("\nLooking for liabilities section...")
    section, table = find_section_and_table('Part 7. Liabilities')
    if section and table:
        print("Found liabilities section")
        data['liabilities'] = extract_table_data(table, 'liabilities')
    else:
        print("No liabilities section found")

    # Extract positions (Part 8)
    print("\nLooking for positions section...")
    section, table = find_section_and_table('Part 8. Positions')
    if section and table:
        print("Found positions section")
        data['positions'] = extract_table_data(table, 'positions')
    else:
        print("No positions section found")

    # Extract agreements (Part 9)
    print("\nLooking for agreements section...")
    section, table = find_section_and_table('Part 9. Agreements')
    if section and table:
        print("Found agreements section")
        data['agreements'] = extract_table_data(table, 'agreements')
    else:
        print("No agreements section found")

    print("\nParsing complete. Returning data structure...")
    return data

# Example use:
html_content = fetch_senate_disclosure("13b4ce32-26e4-48e5-834c-85159fbe7022")
if html_content:
    print("HTML content received, length:", len(html_content))
    structured_data = parse_senate_disclosure(html_content)
    print("\nFinal structured data:")
    print(json.dumps(structured_data, indent=2))
else:
    print("No HTML content received from fetch_senate_disclosure")
