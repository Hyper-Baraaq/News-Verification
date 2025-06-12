from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException
from typing import Tuple

class URLValidator:
    """Class to validate URL format and accessibility"""

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate URL format and accessibility"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format. Please include http:// or https://"
            
            if result.scheme not in ['http', 'https']:
                return False, "Only HTTP and HTTPS protocols are supported"
            
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code >= 400:
                return False, f"URL is not accessible (Status code: {response.status_code})"
                
            return True, "URL is valid and accessible"
            
        except RequestException as e:
            return False, f"Cannot access URL: {str(e)}"
        except Exception as e:
            return False, f"URL validation error: {e}"