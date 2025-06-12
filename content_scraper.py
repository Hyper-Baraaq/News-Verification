import requests
from bs4 import BeautifulSoup, Comment
import re
from urllib.parse import urlparse
import dateutil.parser
from typing import Tuple, Dict, Any

class ContentScraper:
    """Class to fetch, clean, and extract metadata from HTML content"""

    def fetch_html_content(self, url: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Fetch HTML content from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            metadata = {
                'content_length': len(response.content),
                'content_type': response.headers.get('content-type', ''),
                'encoding': response.encoding,
                'status_code': response.status_code,
                'final_url': response.url
            }
            
            return True, response.text, metadata
            
        except Exception as e:
            return False, f"Failed to fetch content: {str(e)}", {}

    def extract_metadata_from_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML content"""
        metadata = {
            'domain': urlparse(url).netloc,
            'title': None,
            'author': None,
            'publication_date': None,
            'description': None
        }
        
        if soup.title:
            metadata['title'] = soup.title.string.strip() if soup.title.string else None
        
        author_selectors = [
            {'name': 'author'},
            {'property': 'article:author'},
            {'name': 'article:author_name'},
            {'itemprop': 'author'},
            {'class': 'author-name'},
            {'class': 'by-author'},
            {'rel': 'author'}
        ]
        
        for selector in author_selectors:
            author_elem = soup.find('meta', attrs=selector)
            if author_elem and author_elem.get('content'):
                metadata['author'] = author_elem['content'].strip()
                break
        
        if not metadata['author']:
            for tag in ['span', 'div', 'p', 'a']:
                author_elem = soup.find(tag, class_=re.compile(r'author|by-line|byline', re.I))
                if author_elem:
                    text = author_elem.get_text(strip=True)
                    if text and len(text) < 100:
                        metadata['author'] = text.replace('By', '').replace('by', '').strip()
                        break
        
        date_selectors = [
            {'property': 'article:published_time'},
            {'name': 'publish_date'},
            {'name': 'publication_date'},
            {'property': 'article:published'},
            {'itemprop': 'datePublished'},
            {'name': 'article_date_time'},
            {'property': 'og:article:published_time'}
        ]
        
        for selector in date_selectors:
            date_elem = soup.find('meta', attrs=selector)
            if date_elem and date_elem.get('content'):
                try:
                    parsed_date = dateutil.parser.parse(date_elem['content'])
                    metadata['publication_date'] = parsed_date.strftime('%Y-%m-%d')
                    break
                except:
                    continue
        
        if not metadata['publication_date']:
            time_elem = soup.find('time')
            if time_elem:
                datetime_attr = time_elem.get('datetime')
                if datetime_attr:
                    try:
                        parsed_date = dateutil.parser.parse(datetime_attr)
                        metadata['publication_date'] = parsed_date.strftime('%Y-%m-%d')
                    except:
                        pass
        
        desc_elem = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'})
        if desc_elem and desc_elem.get('content'):
            metadata['description'] = desc_elem['content'].strip()
        
        return metadata
    
    def clean_html(self, html_content: str, url: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Clean and preprocess HTML content, also extract metadata"""
        original_size = len(html_content)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        metadata = self.extract_metadata_from_html(soup, url)
        
        title = soup.title.string.strip() if soup.title and soup.title.string else "No title found"
        
        for tag in soup.find_all(['script', 'style', 'svg', 'iframe', 'noscript']):
            tag.decompose()
        
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        if soup.head:
            head_title = soup.head.title
            soup.head.clear()
            if head_title:
                soup.head.append(head_title)
        
        main_content = None
        content_selectors = [
            'article', 'main', '[role="main"]', '.content', '#content', 
            '.post', '.article', '.article-body', '.story-body'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements
                break
        
        if main_content:
            new_soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
            for element in main_content:
                new_soup.body.append(element)
            cleaned_html = str(new_soup)
        else:
            cleaned_html = str(soup)
        
        cleaned_html = re.sub(r'\s+', ' ', cleaned_html).strip()
        cleaned_html = re.sub(r'>\s+<', '><', cleaned_html)
        
        cleaned_size = len(cleaned_html)
        
        if cleaned_size > 500000:
            text_only = ' '.join(soup.stripped_strings)
            cleaned_html = f"<html><body><p>{text_only}</p></body></html>"
            cleaned_size = len(cleaned_html)
        
        stats = {
            'original_size': original_size,
            'cleaned_size': cleaned_size,
            'reduction_percent': round(((original_size - cleaned_size) / original_size * 100), 2),
            'title': title,
            'content_found': main_content is not None
        }
        
        return cleaned_html, stats, metadata