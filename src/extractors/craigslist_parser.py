thonfrom bs4 import BeautifulSoup

class CraigslistParser:
    def __init__(self):
        pass
    
    def parse_listing_page(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        listings = []
        for row in soup.find_all('li', class_='result-row'):
            listing = {
                'id': row.get('data-id'),
                'url': row.find('a').get('href'),
                'title': row.find('a').text,
                'datetime': row.find('time')['datetime'],
                'location': row.find('span', class_='result-hood').text if row.find('span', class_='result-hood') else '',
                'category': row.get('class', [None])[0],
                'price': row.find('span', class_='result-price').text if row.find('span', class_='result-price') else '',
                'post': row.find('a').text,
                'notices': [],
                'phoneNumbers': [],
                'pics': []
            }
            listings.append(listing)
        return listings