thonimport requests
import json
import os
from extractors.craigslist_parser import CraigslistParser
from outputs.exporters import export_to_json
from config.settings import PROXY_CONFIG

class CraigslistScraper:
    def __init__(self, category, location, output_format='json'):
        self.category = category
        self.location = location
        self.output_format = output_format
        self.parser = CraigslistParser()
    
    def fetch_listings(self, page=1):
        url = f"https://{self.location}.craigslist.org/search/{self.category}?s={page * 120}"
        response = requests.get(url, proxies=PROXY_CONFIG)
        listings = self.parser.parse_listing_page(response.text)
        return listings
    
    def save_data(self, data):
        output_path = os.path.join('data', f"{self.category}_{self.location}_scrape.{self.output_format}")
        export_to_json(data, output_path)

    def scrape(self, num_pages=5):
        all_listings = []
        for page in range(num_pages):
            listings = self.fetch_listings(page)
            all_listings.extend(listings)
        self.save_data(all_listings)

if __name__ == "__main__":
    scraper = CraigslistScraper(category='jobs', location='newyork')
    scraper.scrape()