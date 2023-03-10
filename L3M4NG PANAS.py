import pandas as pd
import logging
from bs4 import BeautifulSoup
import requests
import requests.exceptions
import urllib.parse
from collections import deque
import re
import json

def search_crtsh(domain):
    subdomains = []
    try:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.text)
            for item in data:
                subdomains.append(item['name_value'].lower())
    except Exception as e:
        print(f'[ERROR] Failed to search CRT.sh for {domain}: {e}')
    return subdomains

# Configure logging
logging.basicConfig(filename='web_scraper.log', level=logging.ERROR, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

user_url = input('[+] Enter your target:')
subdomains = [user_url.split(".")[0]] + search_crtsh(user_url)

emails_addresses = {}
for subdomain in subdomains:
    urls = deque([f"{subdomain}.{user_url.split('.', 1)[1]}"])
    scraped_urls = set()

    count = 0
    try:
        while len(urls):
            count += 1
            if count == 400:
                break
            url = urls.popleft()
            if url in scraped_urls:
                continue
            scraped_urls.add(url)

            parts = urllib.parse.urlsplit(url)
            base_url = '{0.scheme}://{0.netloc}'.format(parts)

            # to find the last occurrence of the '/' character in "url
            path = url[:url.rfind('/') + 1] if '/' in parts.path else url

            print(f'[{count}] Processing {url}')
            try:
                response = requests.get(url, timeout=10, verify=False)
                response.raise_for_status()
            except (requests.exceptions.MissingSchema,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.RequestException,
                    requests.exceptions.HTTPError) as e:
                logging.error(f"[ERROR] {e} in url: {url}")
                continue

            #To search for email addresses in the response.text and returns a list of all the matches found.
            new_emails = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', response.text)

            if base_url in emails_addresses:
                emails_addresses[base_url].update(new_emails)
            else:
                emails_addresses[base_url] = set(new_emails)

            # parsing and navigating an HTML or XML document
            soup = BeautifulSoup(response.text, features="lxml")

            for anchor in soup.find_all("a"):
                link = anchor.attrs['href'] if 'href' in anchor.attrs else ''
                if link.startswith('/'):
                    link = base_url + link
                elif not link.startswith('http'):
                    link = path + link
                if not link in urls and not link in scraped_urls:
                    urls.append(link)
    except KeyboardInterrupt:
        print('[-] Closing!')
  
# Create a DataFrame from the emails list

df = pd.DataFrame({'emails': [email for emails in emails_addresses.values() for email in emails], 'url': [url for url in emails_addresses.keys() for _ in range(len(emails_addresses[url]))]})

# Sort the DataFrame by the 'site' column
df.sort_values("url", inplace=True)

# Export the DataFrame to an Excel file
df.to_excel("emails_web scraper.xlsx", index=False, columns=["emails", "url"])