from typing import Tuple, Dict, Any
from config import CONFIG

class ConfidenceCalculator:
    """Class to calculate confidence scores for content credibility"""

    def calculate_confidence_score(
        self,
        perplexity_analysis: Dict[str, Any],
        extracted_text: str,
        metadata: Dict[str, Any],
        source_credibility_score: float,
        url_valid: bool = True
    ) -> Tuple[float, str, Dict[str, Any]]:
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
        domain = metadata.get('domain', '').lower()

        # -----------------------------
        # CONTENT CONSISTENCY SCORING
        # -----------------------------
        facts = perplexity_analysis.get('fact_verification', [])
        if facts:
            verified_count = sum(1 for fact in facts if fact['status'] == 'Verified')
            total_count = len(facts)
            ratio = verified_count / total_count if total_count else 0
            scores['content_consistency'] = ratio * 0.95
            if ratio < 0.5:
                scores['content_consistency'] *= 0.3
        else:
            analysis_text = perplexity_analysis.get('full_analysis', '').lower()
            positive_indicators = ['verified', 'confirmed', 'accurate', 'reliable', 'credible', 'supported']
            negative_indicators = ['false', 'misleading', 'disputed', 'incorrect', 'misinformation', 'contradicted']
            positive_count = sum(word in analysis_text for word in positive_indicators)
            negative_count = sum(word in analysis_text for word in negative_indicators)
            total_indicators = positive_count + negative_count
            if total_indicators > 0:
                ratio = positive_count / total_indicators
                scores['content_consistency'] = ratio * 0.9
                if negative_count > positive_count:
                    scores['content_consistency'] *= 0.3
            else:
                scores['content_consistency'] = 0.15
                if domain in trusted_domains:
                    scores['content_consistency'] += 0.3

        # -----------------------------
        # VERIFICATION COVERAGE
        # -----------------------------
        sources = perplexity_analysis.get('sources', [])
        scores['verification_coverage'] = min(len(sources) * 0.3 + len(facts) * 0.2, 0.95) if (facts or sources) else 0.05

        # -----------------------------
        # TEXT QUALITY ADJUSTMENTS
        # -----------------------------
        word_count = len(extracted_text.split())
        if word_count < 100:
            scores['content_consistency'] *= 0.5
            scores['verification_coverage'] *= 0.5
        elif word_count > 600:
            scores['content_consistency'] += 0.05
            scores['verification_coverage'] += 0.05

        # -----------------------------
        # WEIGHTING LOGIC
        # -----------------------------
        is_sensitive = any(keyword in extracted_text.lower() for keyword in sensitive_topics)
        weights = CONFIG["confidence_weights"]["trusted"] if domain in trusted_domains else CONFIG["confidence_weights"]["default"]

        if is_sensitive:
            weights = weights.copy()
            weights['content_consistency'] += CONFIG["confidence_weights"]["sensitive_adjustments"]["content_consistency"]
            weights['verification_coverage'] += CONFIG["confidence_weights"]["sensitive_adjustments"]["verification_coverage"]

        final_score = sum(scores[key] * weights[key] for key in scores)

        # -----------------------------
        # METADATA ASSESSMENT BIAS
        # -----------------------------
        metadata_assessment = perplexity_analysis.get('metadata_assessment', {})
        domain_eval = metadata_assessment.get('domain_credibility', '').lower()
        author_eval = metadata_assessment.get('author_credibility', '').lower()

        if 'not credible' in domain_eval or 'unreliable' in domain_eval:
            final_score *= 0.4
        elif 'credible' in domain_eval:
            final_score *= 1.2

        if 'credible' in author_eval:
            final_score *= 1.15
        elif 'not credible' in author_eval:
            final_score *= 0.6

        # -----------------------------
        # FINAL ADJUSTMENTS
        # -----------------------------
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
