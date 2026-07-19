import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# --- CONFIG ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}


def clean_and_style_html(soup_element, base_url="https://www.sarkariexam.com"):
    """
    Cleans HTML, preserves table formatting, and GUARANTEES clickable links!
    """
    if not soup_element: return ""

    try:
        # 1. REMOVE JUNK TAGS
        for tag in soup_element.find_all(["script", "style", "iframe", "ins", "button", "input", "form", "nav", "footer", "header", "aside", "meta"]):
            if tag: tag.decompose()

        # 2. REMOVE AD DIVS
        for div in soup_element.find_all("div"):
            if div:
                classes = str(div.get("class", [])).lower()
                id_name = str(div.get("id", "")).lower()
                if "ad" in classes or "ad" in id_name or "sponsored" in classes:
                    div.decompose()

        # 3. STYLE TABLES
        for table in soup_element.find_all("table"):
            table['class'] = "table table-bordered"
            table['style'] = "width: 100%; margin-top: 15px; margin-bottom: 25px; background: #ffffff; border: 1px solid #dee2e6;"
            
            thead = table.find("thead")
            if thead:
                thead['style'] = "background-color: #f8fafc; color: #1f2937; font-weight: bold;"
            else:
                first_row = table.find("tr")
                if first_row: 
                    first_row['style'] = "background-color: #f8fafc; color: #1f2937; font-weight: bold; text-align: center;"

        # 4. 🔥 THE FIX: MODIFY TAGS IN-PLACE WITHOUT ERASING LINKS! 🔥
        for header in soup_element.find_all(["h1", "h2", "h3", "h4"]):
            # If this header is inside a table cell, convert to simple span so it doesn't break table layout or erase links!
            if header.find_parent("table"):
                header.name = "span"
                continue
                
            # Modify tag in-place so child tags (like <a href="...">) are NEVER deleted!
            header.name = "h4"
            header['style'] = "margin-top: 25px; margin-bottom: 15px; color: #1f2937; font-weight: bold; font-size: 1.15rem; border-left: 4px solid #b91c1c; padding-left: 10px;"

        # 5. 🔥 GUARANTEE EVERY LINK IS CLICKABLE & BLUE 🔥
        for a in soup_element.find_all("a"):
            href = a.get("href")
            if href and href != "#" and "javascript:" not in href.lower():
                # Convert relative URLs to full website links
                full_url = urljoin(base_url, href)
                a['href'] = full_url
                a['target'] = "_blank"  # Open in new tab
                a['rel'] = "noopener noreferrer"
                
                # Force bright blue clickable link styling
                a['style'] = "color: #2563eb !important; font-weight: 700 !important; text-decoration: underline !important; cursor: pointer !important; display: inline !important;"
                
                # Clean out Bootstrap classes that might disable clicks
                if a.has_attr('class'):
                    a['class'] = [c for c in a['class'] if not any(x in c for x in ['disabled', 'btn', 'pe-none'])]

        return str(soup_element)

    except Exception as e:
        print(f"      ⚠️ Styling Error: {e}")
        return str(soup_element)

def extract_dates(soup):
    """
    Scans table rows and lists specifically to find accurate Start/End dates.
    """
    start_date = "Not Specified"
    last_date = "Check Notice"
    
    # Regex to catch: 12 Jan 2026, 12/01/2026, 12-01-2026
    date_pattern = r'(\d{1,2}[\s\./-](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[a-zA-Z]+|\d{1,2})[\s\./-]\d{2,4})'

    # We look inside specific tags where dates usually hide (Lists, Table Rows, Paragraphs)
    date_candidates = soup.find_all(['li', 'tr', 'p', 'td', 'div'])
    
    for tag in date_candidates:
        text = tag.get_text(" ", strip=True).lower()
        
        # SKIP if the line contains "admit card" or "result" (prevents grabbing wrong dates)
        if "admit" in text or "result" in text or "answer" in text:
            continue

        # --- 1. FIND START DATE (Updated with your screenshots keywords) ---
        # Added: 'application start', 'registration starting'
        if any(kw in text for kw in ['application start', 'starting date', 'registration starting', 'registration start', 'application begin', 'open form']):
            match = re.search(date_pattern, text, re.IGNORECASE)
            if match:
                start_date = match.group(1)
        
        # --- 2. FIND LAST DATE ---
        if any(kw in text for kw in ['last date', 'closing date', 'end date', 'apply online upto', 'registration last']):
            # Avoid confusing "Fee Payment Last Date" with the actual "Form Last Date"
            if "fee" not in text or last_date == "Check Notice":
                match = re.search(date_pattern, text, re.IGNORECASE)
                if match:
                    last_date = match.group(1)

    return start_date, last_date

def scrape_job_smartly(url):
    print(f"   📖 Reading Page: {url}...")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        if response.status_code != 200: 
            print(f"      ❌ Page Load Failed: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- A. TITLE ---
        title_tag = soup.find('h1')
        if not title_tag: title_tag = soup.find('h2')
        job_title = title_tag.get_text(strip=True) if title_tag else "Govt Job Notification"

        # --- B. FIND CONTENT ---
        print("      🔍 Searching for content box...")
        content = soup.find('div', class_='post-content') or soup.find('article') or soup.find('div', id='post-content')
        
        final_html = ""
        
        if content:
            print("      ✅ Found Content Box. Cleaning...")
            # PASS THE URL HERE:
            final_html = clean_and_style_html(content, base_url=url) 
        else:
            print("      ⚠️ Main box missing. Switching to Table Vacuum.")
            all_tables = soup.find_all('table')
            if all_tables:
                print(f"      ✅ Found {len(all_tables)} tables.")
                temp_html = "<h4>Job Details</h4>"
                for t in all_tables:
                    temp_html += str(t) + "<br>"
                
                temp_soup = BeautifulSoup(temp_html, 'html.parser')
                # PASS THE URL HERE AS WELL:
                final_html = clean_and_style_html(temp_soup, base_url=url)

        # Check if we got anything
        if not final_html or len(final_html) < 50:
            print("      ❌ No data extracted (Empty).")
            return None

        # --- C. META DATA ---
        full_text = soup.get_text(" ", strip=True)
        
        # 1. Fees (Preserved from your code)
        fees = "See Notice"
        fee_match = re.search(r'(General|Gen|OBC|EWS).*?(\d{2,4})', full_text, re.IGNORECASE)
        if fee_match: fees = fee_match.group(0)

        # 2. Extract Dates (Using the Smart Helper Function)
        start_date, last_date = extract_dates(soup)

        print(f"      🎉 Success! Extracted {len(final_html)} bytes.")
        return {
            "title": job_title,
            "company": "Govt Org", 
            "location": "India",
            "salary": "As Per Rules",
            "skills": fees,
            "last_date": last_date,
            "start_date": start_date, 
            "description": final_html, 
            "source_link": url
        }

    except Exception as e:
        print(f"      ❌ Critical Crash: {e}")
        return None
