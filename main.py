import streamlit as st
import json
from datetime import datetime
from urllib.parse import urlparse
import time
from url_validator import URLValidator
from content_scraper import ContentScraper
from source_credibility_evaluator import SourceCredibilityEvaluator
from content_analyzer import ContentAnalyzer
from confidence_calculator import ConfidenceCalculator
from database_manager import DatabaseManager
from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path
from urllib.parse import urlparse
import hashlib
from config import CONFIG

# Page configuration
st.set_page_config(
    page_title="URL Verification System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: rgb(0, 204, 150);
    }
    .success-box {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-color: #ffeeba;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'verification_history' not in st.session_state:
    st.session_state.verification_history = []
if 'current_verification' not in st.session_state:
    st.session_state.current_verification = None
if 'url_cache' not in st.session_state:
    st.session_state.url_cache = {}
if 'add_to_cache' not in st.session_state:
    st.session_state.add_to_cache = False
if 'current_result' not in st.session_state:
    st.session_state.current_result = None

def display_results(verification_result: Dict[str, Any]):
    """Display verification results in a user-friendly format"""
    st.header("📊 Verification Results")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        score = verification_result['confidence_score']
        level = verification_result['confidence_level']
        
        if score >= 0.75:
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.metric("Confidence Score", f"{score:.1%}", "High Confidence")
        elif score >= 0.3:
            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
            st.metric("Confidence Score", f"{score:.1%}", "Medium Confidence")
        else:
            st.markdown('<div class="error-box">', unsafe_allow_html=True)
            st.metric("Confidence Score", f"{score:.1%}", "Low Confidence")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.subheader("Score Components")
        components = verification_result['score_components']
        for component, value in components.items():
            st.progress(value, text=f"{component.replace('_', ' ').title()}: {value:.1%}")
    
    with col3:
        st.subheader("Verified")
        st.write(verification_result['timestamp'])
    
    if 'metadata_assessment' in verification_result:
        with st.expander("🔍 Source Metadata Assessment", expanded=True):
            metadata_assess = verification_result['metadata_assessment']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Domain Credibility")
                st.write(metadata_assess.get('domain_credibility', 'Not assessed'))
            
            with col2:
                st.subheader("Author Credibility")
                st.write(metadata_assess.get('author_credibility', 'Not assessed'))
            
            with col3:
                st.subheader("Date Relevance")
                st.write(metadata_assess.get('date_relevance', 'Not assessed'))
    
    if 'fact_verification' in verification_result and verification_result['fact_verification']:
        with st.expander("✓ Fact Verification Results", expanded=True):
            facts = verification_result['fact_verification']
            
            verified_count = sum(1 for f in facts if f['status'] == 'Verified')
            disputed_count = len(facts) - verified_count
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Verified Claims", verified_count)
            with col2:
                st.metric("Disputed Claims", disputed_count, delta_color="inverse")
            
            st.divider()
            
            for fact in facts:
                if fact['status'] == 'Verified':
                    st.success(f"✓ {fact['claim']}")
                else:
                    st.warning(f"⚠ {fact['claim']}")
    
    with st.expander("📝 Detailed Analysis", expanded=True):
        if 'extracted_text' in verification_result:
            extracted = verification_result['extracted_text']
            if 'METADATA SECTION' in extracted or 'Website Domain' in extracted:
                metadata_end = extracted.find('\n\n2.') or extracted.find('\n\nKEY CLAIMS')
                if metadata_end != -1:
                    st.subheader("Extracted Metadata")
                    st.code(extracted[:metadata_end])
                    st.subheader("Key Claims and Facts")
                    st.text_area(
                        label="Extracted Text",
                        value=extracted[:1500] + "...",
                        height=300,
                        label_visibility="collapsed"
                    )

                else:
                    st.subheader("Extracted Content")
                    st.text_area(
                        label="Extracted Text",
                        value=extracted[:1500] + "...",
                        height=300,
                        label_visibility="collapsed"
                    )

            else:
                st.subheader("Extracted Content")
                st.text_area(
                    label="Extracted Text",
                    value=extracted[:1500] + "...",
                    height=300,
                    label_visibility="collapsed"
                )

        
        st.subheader("Credibility Assessment")
        st.write(verification_result['credibility_assessment'])
        
        if verification_result['sources']:
            st.subheader("Supporting Sources")
            for i, source in enumerate(verification_result['sources'], 1):
                st.write(f"{i}. {source}")

def main():
    """Main Streamlit application"""
    st.title("🔍 URL Verification System")
    st.markdown("Verify the credibility of online content using AI-powered analysis")
    
    with st.sidebar:
        st.header("🔐 API Configuration")
        openai_key = st.text_input("OpenAI API Key", type="password", key="openai_key", value=CONFIG["openai_api_key"])
        perplexity_key = st.text_input("Perplexity API Key", type="password", key="perplexity_key", value=CONFIG["perplexity_api_key"])
        
        if openai_key and perplexity_key:
            st.success("✅ API keys configured")
        else:
            st.warning("⚠️ Please enter both API keys")
        
        st.divider()
        st.header("📜 Verification History")
        if st.session_state.verification_history:
            for item in st.session_state.verification_history[-5:]:
                st.write(f"• {item['url'][:30]}... - {item['score']:.1%}")
        else:
            st.info("No verifications yet")
    
    url_input = st.text_input("Enter URL to verify", placeholder="https://example.com/article")
    
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        verify_button = st.button("🚀 Verify URL", type="primary", disabled=not (url_input and openai_key and perplexity_key))
    with col2:
        if st.button("🗑️ Clear History"):
            st.session_state.verification_history = []
            st.session_state.url_cache = {}
            st.session_state.add_to_cache = False
            st.session_state.current_result = None
            st.rerun()
    
    if verify_button and url_input:
        # Initialize classes
        db_manager = DatabaseManager()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            start_time = time.time()
            
            # Step 1: Check domain_credibility table
            domain = urlparse(url_input).netloc
            trust_score = db_manager.get_trust_score_from_db(domain)
            if trust_score is not None:
                result = {
                    'url': url_input,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'confidence_score': trust_score,
                    'confidence_level': (
                        f"🟢 Confidence Level: HIGH ({trust_score:.2%})" if trust_score >= 0.75 else
                        f"🟡 Confidence Level: MEDIUM ({trust_score:.2%})" if trust_score >= 0.3 else
                        f"🔴 Confidence Level: LOW ({trust_score:.2%})"
                    ),
                    'score_components': {'source_credibility': trust_score, 'content_consistency': 0.0, 'verification_coverage': 0.0},
                    'extracted_text': '',
                    'credibility_assessment': f"Domain {domain} found in credibility database with trust score {trust_score:.2%}",
                    'sources': [],
                    'full_analysis': '',
                    'metadata_assessment': {'domain_credibility': f"Trust score: {trust_score:.2%}"},
                    'fact_verification': []
                }
                st.session_state.current_verification = result
                st.session_state.verification_history.append({
                    'url': url_input,
                    'score': result['confidence_score'],
                    'timestamp': result['timestamp']
                })
                st.session_state.url_cache[url_input] = result
                progress_bar.progress(100)
                status_text.text("✅ Retrieved from domain credibility database!")
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                display_results(result)
                return
            
            # Step 2: Proceed with full verification
            url_validator = URLValidator()
            content_scraper = ContentScraper()
            source_credibility_evaluator = SourceCredibilityEvaluator()
            content_analyzer = ContentAnalyzer()
            confidence_calculator = ConfidenceCalculator()
            
            # Initialize result dictionary
            result = {
                'url': url_input,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'confidence_score': 0.0,
                'confidence_level': "🔴 Confidence Level: NONE (0%)",
                'score_components': {'source_credibility': 0.0, 'content_consistency': 0.0, 'verification_coverage': 0.0},
                'extracted_text': '',
                'credibility_assessment': '',
                'sources': [],
                'full_analysis': '',
                'metadata_assessment': {},
                'fact_verification': []
            }
            
            # Step 3: Validate URL
            status_text.text("🔍 Validating URL...")
            progress_bar.progress(10)
            is_valid, validation_msg = url_validator.validate_url(url_input)
            if not is_valid:
                result['credibility_assessment'] = validation_msg
                st.session_state.current_result = result
                display_results(result)
                return
            
            # Step 4: Fetch HTML
            status_text.text("📥 Fetching content...")
            progress_bar.progress(20)
            success, html_content, metadata = content_scraper.fetch_html_content(url_input)
            if not success:
                result['credibility_assessment'] = html_content
                st.session_state.current_result = result
                display_results(result)
                return
            
            # Step 5: Clean HTML
            status_text.text("🧹 Cleaning content...")
            progress_bar.progress(40)
            cleaned_html, clean_stats, extracted_metadata = content_scraper.clean_html(html_content, url_input)
            result.update({
                'domain': extracted_metadata.get('domain'),
                'title': extracted_metadata.get('title'),
                'author': extracted_metadata.get('author'),
                'publication_date': extracted_metadata.get('publication_date'),
                'content_type': metadata.get('content_type'),
                'content_length': metadata.get('content_length', 0)
            })
            
            # Step 6: Extract text with OpenAI
            status_text.text("📝 Extracting text...")
            progress_bar.progress(60)
            success, extracted_text, extract_metadata = content_analyzer.extract_text_with_openai(cleaned_html, extracted_metadata)
            if not success:
                result['credibility_assessment'] = extracted_text
                st.session_state.current_result = result
                display_results(result)
                return
            result['extracted_text'] = extracted_text
            result['openai_tokens_used'] = extract_metadata.get('tokens_used', 0)
            result['extraction_model'] = extract_metadata.get('extraction_model', 'gpt-4o-mini')
            
            # Step 7: Analyze with Perplexity
            status_text.text("🔎 Analyzing credibility...")
            progress_bar.progress(80)
            success, analysis_results = content_analyzer.analyze_with_perplexity(extracted_text)
            if not success:
                result['credibility_assessment'] = analysis_results.get('error', 'Analysis failed')
                result['confidence_score'] = 0.1
                result['confidence_level'] = "🔴 Confidence Level: LOW (10%)"
                result['score_components'] = {'source_credibility': 0.1, 'content_consistency': 0.1, 'verification_coverage': 0.1}
                st.session_state.current_result = result
                display_results(result)
                return
            result.update({
                'credibility_assessment': analysis_results.get('credibility_assessment', 'N/A'),
                'sources': analysis_results.get('sources', []),
                'full_analysis': analysis_results.get('full_analysis', ''),
                'metadata_assessment': analysis_results.get('metadata_assessment', {}),
                'fact_verification': analysis_results.get('fact_verification', [])
            })
            
            # Step 8: Evaluate source credibility
            source_credibility_score = source_credibility_evaluator.evaluate_source_credibility(extracted_metadata)
            
            # Step 9: Calculate confidence score
            status_text.text("📊 Calculating confidence...")
            progress_bar.progress(90)
            confidence_score, confidence_explanation, score_components = confidence_calculator.calculate_confidence_score(
                analysis_results, extracted_text, extracted_metadata, source_credibility_score, url_valid=True
            )
            
            # Step 10: Insert into domain_credibility
            notes = f"Automatically added domain based on analysis: {analysis_results.get('credibility_assessment', 'No assessment')}"
            db_manager.insert_domain(
                domain, confidence_score, extracted_metadata.get('category', 'general'), 
                extracted_metadata.get('bias_level', 'unknown'), extracted_metadata.get('reliability', 'unknown'), notes
            )
            
            # Update result
            result.update({
                'confidence_score': confidence_score,
                'confidence_level': confidence_explanation,
                'score_components': score_components,
                'perplexity_calls_made': 1
            })
            
            st.session_state.current_verification = result
            st.session_state.verification_history.append({
                'url': url_input,
                'score': result['confidence_score'],
                'timestamp': result['timestamp']
            })
            st.session_state.url_cache[url_input] = result
            st.session_state.current_result = result
            
            processing_time = time.time() - start_time
            
            progress_bar.progress(100)
            status_text.text("✅ Verification completed!")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
            
            display_results(result)
            
            # Step 11: Prompt user to add to url_verification_cache
            st.subheader("💾 Save to Cache")
            if st.button("Add Results to Database Cache"):
                db_manager.insert_cached_result(result, processing_time)
                st.success("✅ Results added to URL verification cache!")
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📄 Download JSON Report",
                    data=json.dumps(result, indent=2),
                    file_name=f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            progress_bar.empty()
            status_text.empty()

if __name__ == "__main__":
    main()