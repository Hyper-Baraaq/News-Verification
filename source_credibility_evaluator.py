from datetime import datetime
from typing import Dict, Any
from config import CONFIG

class SourceCredibilityEvaluator:
    """Class to evaluate source credibility based on domain, author, and date"""

    def evaluate_source_credibility(self, metadata: Dict[str, Any]) -> float:
        """Evaluate source credibility based on metadata"""
        trusted_domains = CONFIG["trusted_domains"]
        untrusted_domains = CONFIG["untrusted_domains"]
        default_domain_score = CONFIG["default_domain_score"]

        domain = metadata.get('domain', '').lower()
        author = metadata.get('author', None)
        pub_date = metadata.get('publication_date', None)

        if domain in untrusted_domains:
            credibility_score = untrusted_domains[domain]
        else:
            credibility_score = trusted_domains.get(domain, default_domain_score)

        if author and author.lower() != 'none':
            credibility_score += 0.15
        elif domain not in trusted_domains:
            credibility_score -= 0.1
        else:
            credibility_score -= 0.05

        if pub_date:
            try:
                pub_date_obj = datetime.strptime(pub_date, '%Y-%m-%d')
                days_old = (datetime.now() - pub_date_obj).days
                if days_old > 365:
                    penalty = 0.15 if domain in trusted_domains else 0.25
                    credibility_score -= penalty
                elif days_old < 30:
                    credibility_score += 0.15
            except ValueError:
                pass
        elif domain not in trusted_domains:
            credibility_score -= 0.05
        else:
            credibility_score -= 0.02

        return max(0.0, min(1.0, credibility_score))