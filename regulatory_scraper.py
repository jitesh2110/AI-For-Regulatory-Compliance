import os
import json
import urllib.parse
import re
import time
from bs4 import BeautifulSoup

# Standard requests for FSSAI
import requests

# curl_cffi for SEBI & RBI
from curl_cffi import requests as c_requests

# Create a GLOBAL persistent session to hold WAF cookies!
hybrid_session = c_requests.Session(impersonate="chrome")

# Playwright for MCA
from playwright.sync_api import sync_playwright

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloaded_notices")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ENDPOINTS = {
    "SEBI_Circular": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0",
    "RBI_Notification": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
    "RBI_Master_Direction": "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx",
    "MCA_Notification": "https://www.mca.gov.in/content/mca/global/en/acts-rules/ebooks/notifications.html",
    "FSSAI_Advisory": "https://www.fssai.gov.in/advisories.php"
}

def download_pdf_cffi(pdf_url, endpoint_name):
    """Downloads the PDF via curl_cffi module holding persistent cookies."""
    if not pdf_url or pdf_url.lower().startswith("javascript:"): 
        return None
    try:
        print(f"    -> Downloading PDF (c_requests) for {endpoint_name}: {pdf_url}")
        stealth_headers = {
            "Referer": "https://www.sebi.gov.in/",
            "Accept": "application/pdf, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        # Using the global hybrid_session so cookies are attached
        response = hybrid_session.get(pdf_url, timeout=60, headers=stealth_headers)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        if 'application/pdf' not in content_type.lower():
            print(f"       [!] Server returned {content_type} instead of a PDF. WAF Blocked the download.")
            return None
            
        safe_name = f"{endpoint_name}_latest_notice.pdf"
        file_path = os.path.join(DOWNLOAD_DIR, safe_name)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    except Exception as e:
        print(f"    -> Failed to download PDF (cffi) from {pdf_url}: {e}")
        return None

def download_pdf_standard(pdf_url, endpoint_name):
    """Downloads the PDF using std python requests module."""
    if not pdf_url or pdf_url.lower().startswith("javascript:"): 
        return None
    try:
        print(f"    -> Downloading PDF (standard requests) for {endpoint_name}: {pdf_url}")
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        if 'application/pdf' not in content_type.lower():
            print(f"       [!] Server returned {content_type} instead of a PDF. WAF Blocked the download.")
            return None
            
        safe_name = f"{endpoint_name}_latest_notice.pdf"
        file_path = os.path.join(DOWNLOAD_DIR, safe_name)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    except Exception as e:
        print(f"    -> Failed to download PDF (standard) from {pdf_url}: {e}")
        return None

def scrape_sebi(endpoint_name, url):
    """Hybrid Strategy 1: curl_cffi with Two-Hop Iframe Logic (SEBI)"""
    print(f"[*] Attempting to scrape {endpoint_name}...")
    try:
        # HOP 1: Get the index page using our persistent hybrid_session
        response = hybrid_session.get(url, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first circular link (handles both standard and master circulars)
        article_link = soup.find('a', href=lambda h: h and ("/legal/circulars/" in h.lower() or "/legal/master-circulars/" in h.lower()))
        
        if not article_link:
            print("    -> Could not find a valid SEBI article link on the index page.")
            return None
            
        article_url = urllib.parse.urljoin("https://www.sebi.gov.in", article_link.get('href'))
        title = re.sub(r'\s+', ' ', article_link.get_text(strip=True))
        
        # Extract the date from the parent row for the JSON output
        date_text = "Unknown"
        parent_tr = article_link.find_parent('tr')
        if parent_tr:
            cols = parent_tr.find_all('td')
            if cols:
                date_text = cols[0].get_text(strip=True)
        
        # HOP 2: Navigate into the article to find the embedded PDF iframe/source
        article_response = hybrid_session.get(article_url, timeout=60)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        
        pdf_src = None
        # SEBI often embeds in an iframe
        iframe = article_soup.find('iframe', src=lambda s: s and s.lower().endswith('.pdf'))
        if iframe:
            pdf_src = iframe.get('src')
        else:
            # Fallback to direct anchor tags if no iframe exists
            pdf_a = article_soup.find('a', href=lambda h: h and h.lower().endswith('.pdf'))
            if pdf_a:
                pdf_src = pdf_a.get('href')
                
        if pdf_src:
            # Construct the full URL
            pdf_link = urllib.parse.urljoin(article_url, pdf_src)
            
            # --- CRITICAL FIX: Unwrapping the SEBI Web Viewer ---
            # If the link is trapped in 'web/?file=', extract the actual PDF path
            if "?file=" in pdf_link:
                # Split at the parameter and unquote the URL encoding (e.g. %3A to :)
                pdf_link = urllib.parse.unquote(pdf_link.split("?file=")[-1])
            
            return {
                "endpoint": endpoint_name,
                "date": date_text,
                "title": title,
                "pdf_link": pdf_link,
                "source_url": article_url
            }
        else:
            print(f"    -> Found SEBI article but no PDF source/iframe inside: {article_url}")
            
    except Exception as e:
        print(f"    -> Error scraping {endpoint_name}: {e}")
    return None

def scrape_rbi(endpoint_name, url):
    """Hybrid Strategy 1b: curl_cffi with Two-Hop Logic (RBI)"""
    print(f"[*] Attempting to scrape {endpoint_name}...")
    try:
        # HOP 1: Get the index page
        response = hybrid_session.get(url, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article_url = None
        title = "Unknown RBI Notice"
        date_text = "Unknown"
        
        # Look for the first article link
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                a_tags = row.find_all('a')
                for a in a_tags:
                    href = a.get('href', '')
                    if 'Id=' in href or 'prid=' in href:
                        article_url = urllib.parse.urljoin("https://www.rbi.org.in/Scripts/", href)
                        title = re.sub(r'\s+', ' ', a.get_text(strip=True))
                        date_match = re.search(r'\w{3}\s\d{2},\s\d{4}', row.get_text())
                        if date_match:
                            date_text = date_match.group(0)
                        break
                if article_url:
                    break
            if article_url:
                break
                
        # HOP 2: Navigate into the specific article to find the PDF
        if article_url:
            res2 = hybrid_session.get(article_url, timeout=60)
            soup2 = BeautifulSoup(res2.text, 'html.parser')
            
            pdf_link = None
            for a in soup2.find_all('a'):
                href2 = a.get('href', '')
                if '.pdf' in href2.lower() or 'pdf' in a.get_text(strip=True).lower():
                    pdf_link = urllib.parse.urljoin("https://www.rbi.org.in/Scripts/", href2)
                    break
            
            if pdf_link:
                return {
                    "endpoint": endpoint_name,
                    "date": date_text,
                    "title": title,
                    "pdf_link": pdf_link,
                    "source_url": article_url
                }
            else:
                print(f"    -> Found RBI article but no PDF link inside: {article_url}")
                
    except Exception as e:
        print(f"    -> Error scraping {endpoint_name}: {e}")
    return None

def scrape_fssai(endpoint_name, url):
    """Hybrid Strategy 2: standard requests for Tarpits (FSSAI)"""
    print(f"[*] Attempting to scrape {endpoint_name}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                a_tags = row.find_all('a')
                for a_tag in a_tags:
                    href = a_tag.get('href')
                    if href and ('.pdf' in href.lower() or 'download' in href.lower()):
                        link = urllib.parse.urljoin("https://www.fssai.gov.in/", href)
                        title = cols[1].get_text(strip=True)
                        date_col = next((c for c in cols if re.search(r'\d{2}-\d{2}-\d{4}', c.get_text())), None)
                        date_text = date_col.get_text(strip=True) if date_col else "Unknown"
                        
                        title = re.sub(r'\s+', ' ', title).strip()
                        if title:
                            return {
                                "endpoint": endpoint_name,
                                "date": date_text,
                                "title": title,
                                "pdf_link": link,
                                "source_url": url
                            }
    except Exception as e:
        print(f"    -> Error scraping {endpoint_name}: {e}")
    return None

def scrape_mca(endpoint_name, url):
    """Hybrid Strategy 3: Playwright for AEM/JS Fortress (MCA)"""
    print(f"[*] Attempting to scrape {endpoint_name}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 1. Navigate to the page
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 2. CRITICAL: Specifically wait for any anchor tag that looks like a PDF link
            # This forces Playwright to wait for the JS to actually render the content.
            try:
                page.wait_for_selector("a[href*='.pdf']", timeout=15000)
            except Exception:
                print("    -> Timeout waiting for MCA PDF links. The page might be empty or slow.")

            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for links that contain '/dam/' or end in '.pdf'
            links = soup.find_all('a', href=re.compile(r'/dam/.*|.*\.pdf', re.IGNORECASE))
            
            for a_tag in links:
                title = a_tag.get_text(strip=True)
                link = a_tag.get('href')
                
                # Filter out generic site policies
                if link and title and len(title) > 10 and "policy" not in title.lower():
                    link = urllib.parse.urljoin("https://www.mca.gov.in", link) 
                    
                    # Extract date using regex from the title text
                    date_match = re.search(r'\b\d{1,2}[a-z]{0,2}\s+[A-Za-z]+\s+\d{4}\b|\b\d{2}-\d{2}-\d{4}\b', title)
                    date_text = date_match.group(0) if date_match else "Unknown"
                    
                    title = re.sub(r'\s+', ' ', title).strip()
                    
                    return {
                        "endpoint": endpoint_name,
                        "date": date_text,
                        "title": title,
                        "pdf_link": link,
                        "source_url": url
                    }
    except Exception as e:
        print(f"    -> Error scraping {endpoint_name} via playwright: {e}")
    return None

def main():
    """Main execution entry point."""
    print("Starting Hybrid Script Execution for regulatory portals...\n")
    latest_notices = []
    
    for endpoint_name, url in ENDPOINTS.items():
        notice = None
        download_func = None
        
        if endpoint_name.startswith("SEBI"):
            notice = scrape_sebi(endpoint_name, url)
            download_func = download_pdf_cffi
            
        elif endpoint_name.startswith("RBI"):
            notice = scrape_rbi(endpoint_name, url)
            download_func = download_pdf_cffi
            
        elif endpoint_name.startswith("FSSAI"):
            notice = scrape_fssai(endpoint_name, url)
            download_func = download_pdf_standard
            
        elif endpoint_name.startswith("MCA"):
            notice = scrape_mca(endpoint_name, url)
            download_func = download_pdf_standard 
            
        if notice:
            pdf_url = notice.get("pdf_link")
            if download_func:
                local_path = download_func(pdf_url, endpoint_name)
                if local_path:
                    notice["local_pdf_path"] = local_path
            latest_notices.append(notice)
            
    print(f"\n=======================================================")
    print(f"Total latest notices successfully collected: {len(latest_notices)}")
    print(f"=======================================================\n")
    print(json.dumps(latest_notices, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()