import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

# --- Configuration ---
BASE_URL = "https://search.fibis.org/bin/"

# 10 Explicit datasets to bypass the server's anti-scraping menu blocks
DATASETS = [
    {"name": "Overseas Births 1852", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1249&s_id=791"},
    {"name": "Overseas Births 1853", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1266&s_id=791"},
    {"name": "Overseas Births 1854", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1312&s_id=791"},
    {"name": "Overseas Deaths 1843", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=949&s_id=791"},
    {"name": "Overseas Deaths 1844", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=963&s_id=791"},
    {"name": "Overseas Deaths 1845", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1003&s_id=791"},
    {"name": "Overseas Marriages 1843", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=948&s_id=791"},
    {"name": "Overseas Marriages 1844", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=964&s_id=791"},
    {"name": "Overseas Marriages 1845", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1002&s_id=791"},
    {"name": "Z Mutiny List 1857", "url": "https://search.fibis.org/bin/aps_browse_sources.php?mode=browse_dataset&id=1394&s_id=791"}
]

def scrape_dataset(dataset_name, start_url):
    current_url = start_url
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    safe_name = re.sub(r'[\\/*?:"<>|]', "", dataset_name).strip()
    
    while current_url:
        try:
            response = requests.get(current_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Extract the Data Table
            try:
                tables = pd.read_html(response.text)
                target_table = None
                
                # Find the actual data table (it usually has the most rows/columns)
                for tbl in tables:
                    # We know the table has 'Surname' from your HTML snippet
                    if any('Surname' in str(col) for col in tbl.columns) or len(tbl.columns) >= 4:
                        target_table = tbl
                        break
                
                if target_table is not None:
                    # Clean up the useless "View" column if it exists
                    target_table = target_table.loc[:, ~target_table.columns.str.contains('View|Unnamed', case=False, na=False)]
                    all_data.append(target_table)
                else:
                    return False
            except ValueError:
                return False 
            
            # 2. Pagination based EXACTLY on your HTML snippet: <a title='Next'>
            next_tag = soup.find('a', title='Next')
            
            if next_tag and next_tag.get('href'):
                current_url = urljoin(BASE_URL, next_tag['href'])
                time.sleep(1) # Polite delay
            else:
                current_url = None # Reached the last page
                
        except requests.RequestException:
            print(f"  [!] Network error while scraping {current_url}")
            break

    # 3. Combine Data and Save
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.dropna(how='all', inplace=True) # Remove purely empty rows
        
        if not os.path.exists(safe_name):
            os.makedirs(safe_name)
            
        file_path = os.path.join(safe_name, f"{safe_name}.csv")
        final_df.to_csv(file_path, index=False)
        print(f"  [+] SUCCESS: Saved '{safe_name}' ({len(final_df)} rows)")
        return True
        
    return False

def main():
    print("Starting FIBIS Scraper Pipeline...")
    successful_datasets = 0
    
    for dataset in DATASETS:
        print(f"\nAttempting to scrape: {dataset['name']}")
        success = scrape_dataset(dataset['name'], dataset['url'])
        
        if success:
            successful_datasets += 1
            
    print(f"\n✅ Task 1 Complete! Successfully generated {successful_datasets} datasets.")

if __name__ == "__main__":
    main()