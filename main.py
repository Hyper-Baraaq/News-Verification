from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
from urllib.parse import urlparse
import pytz
import time

from url_validator import URLValidator
from content_scraper import ContentScraper
from source_credibility_evaluator import SourceCredibilityEvaluator
from content_analyzer import ContentAnalyzer
from confidence_calculator import ConfidenceCalculator
from database_manager import DatabaseManager
from config import CONFIG

app = FastAPI(title="URL Verification System")

# In-memory cache
url_cache = {}
verification_history = []

class URLRequest(BaseModel):
    url: str
    openai_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None

class VerificationResponse(BaseModel):
    url: str
    timestamp: str
    verification_datetime: str
    confidence_score: float
    confidence_level: str
    score_components: Dict[str, float]
    extracted_text: str
    credibility_assessment: str
    sources: List[str]
    source_count: int
    online_chatter_score: float
    reliability_score: float
    full_analysis: str
    metadata_assessment: Dict[str, str]
    fact_verification: List[Dict[str, str]]
    openai_tokens_used: Optional[int] = 0
    perplexity_calls_made: Optional[int] = 0
    extraction_model: Optional[str] = "gpt-4o-mini"
    domain: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[str] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = 0

@app.post("/verify", response_model=VerificationResponse)
async def verify_url(request: URLRequest):
    url = request.url
    openai_api_key = request.openai_api_key or CONFIG.get("openai_api_key")
    perplexity_api_key = request.perplexity_api_key or CONFIG.get("perplexity_api_key")

    if not (url and openai_api_key and perplexity_api_key):
        raise HTTPException(status_code=400, detail="URL and both API keys are required")

    db_manager = DatabaseManager()
    cached_result = db_manager.get_cached_result(url)
    if cached_result:
        return cached_result

    try:
        start_time = time.time()
        pkt_tz = pytz.timezone('Asia/Karachi')
        current_datetime = datetime.now(pkt_tz).strftime("%Y-%m-%d %I:%M:%S %p PKT")

        domain = urlparse(url).netloc
        trust_score = db_manager.get_trust_score_from_db(domain)
        if trust_score is not None:
            result = {
                'url': url,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'verification_datetime': current_datetime,
                'confidence_score': trust_score,
                'confidence_level': (
                    f"HIGH ({trust_score:.2%})" if trust_score >= 0.75 else
                    f"MEDIUM ({trust_score:.2%})" if trust_score >= 0.3 else
                    f"LOW ({trust_score:.2%})"
                ),
                'score_components': {'source_credibility': trust_score, 'content_consistency': 0.0, 'verification_coverage': 0.0},
                'extracted_text': '',
                'credibility_assessment': f"Domain {domain} found in credibility database with trust score {trust_score:.2%}",
                'sources': [],
                'source_count': 0,
                'online_chatter_score': 0.0,
                'reliability_score': trust_score,
                'full_analysis': '',
                'metadata_assessment': {'domain_credibility': f"Trust score: {trust_score:.2%}"},
                'fact_verification': []
            }
            url_cache[url] = result
            verification_history.append({
                'url': url,
                'score': result['confidence_score'],
                'timestamp': result['timestamp']
            })
            return result

        # Full pipeline
        url_validator = URLValidator()
        content_scraper = ContentScraper()
        source_credibility_evaluator = SourceCredibilityEvaluator()
        content_analyzer = ContentAnalyzer()
        confidence_calculator = ConfidenceCalculator()

        result = {
            'url': url,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'verification_datetime': current_datetime,
            'confidence_score': 0.0,
            'confidence_level': "None",
            'score_components': {'source_credibility': 0.0, 'content_consistency': 0.0, 'verification_coverage': 0.0},
            'extracted_text': '',
            'credibility_assessment': '',
            'sources': [],
            'source_count': 0,
            'online_chatter_score': 0.0,
            'reliability_score': 0.0,
            'full_analysis': '',
            'metadata_assessment': {},
            'fact_verification': []
        }

        is_valid, validation_msg = url_validator.validate_url(url)
        if not is_valid:
            result['credibility_assessment'] = validation_msg
            return result

        success, html_content, metadata = content_scraper.fetch_html_content(url)
        if not success:
            result['credibility_assessment'] = html_content
            return result

        cleaned_html, clean_stats, extracted_metadata = content_scraper.clean_html(html_content, url)
        result.update({
            'domain': extracted_metadata.get('domain'),
            'title': extracted_metadata.get('title'),
            'author': extracted_metadata.get('author'),
            'publication_date': extracted_metadata.get('publication_date'),
            'content_type': metadata.get('content_type'),
            'content_length': metadata.get('content_length', 0)
        })

        success, extracted_text, extract_metadata = content_analyzer.extract_text_with_openai(cleaned_html, extracted_metadata)
        if not success:
            result['credibility_assessment'] = extracted_text
            return result

        result['extracted_text'] = extracted_text
        result['openai_tokens_used'] = extract_metadata.get('tokens_used', 0)
        result['extraction_model'] = extract_metadata.get('extraction_model', 'gpt-4o-mini')

        success, analysis_results = content_analyzer.analyze_with_perplexity(extracted_text)
        if not success:
            result['credibility_assessment'] = analysis_results.get('error', 'Analysis failed')
            return result

        result.update({
            'credibility_assessment': analysis_results.get('credibility_assessment', 'N/A'),
            'sources': analysis_results.get('sources', []),
            'full_analysis': analysis_results.get('full_analysis', ''),
            'metadata_assessment': analysis_results.get('metadata_assessment', {}),
            'fact_verification': analysis_results.get('fact_verification', [])
        })
        result['source_count'] = len(result['sources'])

        source_credibility_score = source_credibility_evaluator.evaluate_source_credibility(extracted_metadata)
        online_chatter_score = min(0.5 + (len(result['sources']) * 0.1), 1.0)
        if online_chatter_score < 0.3:
            online_chatter_score = 0.3

        reliability_score = (result['confidence_score'] + source_credibility_score) / 2

        confidence_score, confidence_explanation, score_components = confidence_calculator.calculate_confidence_score(
            analysis_results, extracted_text, extracted_metadata, source_credibility_score, url_valid=True
        )

        notes = f"Automatically added domain based on analysis: {analysis_results.get('credibility_assessment', 'No assessment')}"
        db_manager.insert_domain(
            domain, confidence_score, extracted_metadata.get('category', 'general'),
            extracted_metadata.get('bias_level', 'unknown'), extracted_metadata.get('reliability', 'unknown'), notes
        )

        result.update({
            'confidence_score': confidence_score,
            'confidence_level': confidence_explanation,
            'score_components': score_components,
            'perplexity_calls_made': 1,
            'online_chatter_score': online_chatter_score,
            'reliability_score': reliability_score
        })

        url_cache[url] = result
        verification_history.append({
            'url': url,
            'score': result['confidence_score'],
            'timestamp': result['timestamp']
        })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache")
async def cache_result(request: URLRequest):
    url = request.url
    if url not in url_cache:
        raise HTTPException(status_code=404, detail="No verification result found for this URL")
    try:
        db_manager = DatabaseManager()
        db_manager.insert_cached_result(url_cache[url], processing_time=0)
        return {"message": "Results added to cache"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache insert error: {str(e)}")


@app.post("/clear_history")
async def clear_history():
    global url_cache, verification_history
    url_cache = {}
    verification_history = []
    return {"message": "History cleared successfully"}


@app.get("/history")
async def get_history():
    return verification_history[-5:]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)