from typing import Tuple, Dict, Any, List
from config import CONFIG

class ConfidenceCalculator:
    """Class to calculate confidence scores for content credibility"""

    def calculate_confidence_score(self, perplexity_analysis: Dict[str, Any], extracted_text: str, metadata: Dict[str, Any], source_credibility_score: float, url_valid: bool = True) -> Tuple[float, str, Dict[str, Any]]:
        """Calculate confidence score with adjustments for credible sources"""
        if not url_valid:
            return 0.0, "🔴 Confidence Level: NONE (0%) - Invalid or inaccessible URL", {
                'source_credibility': 0.0,
                'content_consistency': 0.0,
                'verification_coverage': 0.0
            }
        
        scores = {
            'source_credibility': source_credibility_score,
            'content_consistency': 0.0,
            'verification_coverage': 0.0
        }
        
        sensitive_topics = CONFIG["sensitive_topics"]
        trusted_domains = CONFIG["trusted_domains"]
        
        facts = perplexity_analysis.get('fact_verification', [])
        if facts:
            verified_count = sum(1 for fact in facts if fact['status'] == 'Verified')
            total_count = len(facts)
            scores['content_consistency'] = (verified_count / total_count) * 0.95 if total_count > 0 else 0.15
            if verified_count / total_count < 0.5:
                scores['content_consistency'] *= 0.3
        else:
            analysis_text = perplexity_analysis.get('full_analysis', '').lower()
            positive_indicators = ['verified', 'confirmed', 'accurate', 'reliable', 'credible', 'supported']
            negative_indicators = ['false', 'misleading', 'disputed', 'incorrect', 'misinformation', 'contradicted']
            positive_count = sum(1 for word in positive_indicators if word in analysis_text)
            negative_count = sum(1 for word in negative_indicators if word in analysis_text)
            total_indicators = positive_count + negative_count
            if total_indicators > 0:
                scores['content_consistency'] = (positive_count / total_indicators) * 0.9
                if negative_count > positive_count:
                    scores['content_consistency'] *= 0.3
            else:
                scores['content_consistency'] = 0.15
                if metadata.get('domain', '').lower() in trusted_domains:
                    scores['content_consistency'] += 0.3
        
        sources = perplexity_analysis.get('sources', [])
        if facts or sources:
            scores['verification_coverage'] = min(len(sources) * 0.3 + len(facts) * 0.2, 0.95)
        else:
            scores['verification_coverage'] = 0.05
        
        is_sensitive = any(keyword in extracted_text.lower() for keyword in sensitive_topics)
        
        weights = CONFIG["confidence_weights"]["trusted"] if metadata.get('domain', '').lower() in trusted_domains else CONFIG["confidence_weights"]["default"]
        if is_sensitive:
            weights = weights.copy()
            weights['content_consistency'] += CONFIG["confidence_weights"]["sensitive_adjustments"]["content_consistency"]
            weights['verification_coverage'] += CONFIG["confidence_weights"]["sensitive_adjustments"]["verification_coverage"]
        
        final_score = sum(scores[key] * weights[key] for key in scores)
        
        metadata_assessment = perplexity_analysis.get('metadata_assessment', {})
        if 'not credible' in metadata_assessment.get('domain_credibility', '').lower() or \
           'unreliable' in metadata_assessment.get('domain_credibility', '').lower():
            final_score *= 0.4
        elif 'credible' in metadata_assessment.get('domain_credibility', '').lower():
            final_score *= 1.2
        if 'credible' in metadata_assessment.get('author_credibility', '').lower():
            final_score *= 1.15
        elif 'not credible' in metadata_assessment.get('author_credibility', '').lower():
            final_score *= 0.6
        
        if len(extracted_text) < 100:
            final_score *= 0.5
        
        final_score = max(0.0, min(1.0, final_score))
        
        if final_score >= 0.75:
            level = "HIGH"
            color = "🟢"
        elif final_score >= 0.3:
            level = "MEDIUM"
            color = "🟡"
        else:
            level = "LOW"
            color = "🔴"
        
        explanation = f"{color} Confidence Level: {level} ({final_score:.2%})"
        
        return final_score, explanation, scores