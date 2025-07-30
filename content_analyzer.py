import openai
import requests
import re
import json
from typing import Tuple, Dict, Any, List
from config import CONFIG
from deep_research_extractor import generate_research_outputs

class ContentAnalyzer:
    """Class to extract and analyze content using OpenAI and Perplexity APIs"""

    def __init__(self):
        self.openai_api_key = CONFIG["openai_api_key"]
        self.perplexity_api_key = CONFIG["perplexity_api_key"]
        self.perplexity_api_url = CONFIG["perplexity_api_url"]

    def extract_text_with_openai(self, cleaned_html: str, metadata: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Extract meaningful text using OpenAI GPT-4o-mini with enhanced metadata extraction"""
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            system_prompt = """You are an expert at extracting meaningful content from HTML for fact-checking purposes.

            Your task is to extract and structure content in the following format:

            1. METADATA SECTION (Always include at the top):
               - Website Domain: [extract from metadata or HTML]
               - Article Title: [extract from title tag or main heading]
               - Author: [extract or indicate 'None' if not found]
               - Publication Date: [extract or indicate 'Not found']

            2. KEY CLAIMS AND FACTS SECTION:
               - Extract major claims/statements as numbered points
               - Include numbers, statistics, quotes, data points
               - Preserve exact wording for key claims
               - Aim for 3–5 verifiable claims if possible

            3. SUPPORTING CONTEXT:
               - Extract relevant context (e.g., background, sources)

            Focus on:
            - Factual claims and statements
            - Numerical data and statistics
            - Direct quotes and attributions
            - Verifiable assertions
            Structure output with clear headers and numbered lists."""
            
            metadata_str = f"""
            Known metadata:
            - Domain: {metadata.get('domain', 'Unknown')}
            - Title: {metadata.get('title', 'Not found')}
            - Author: {metadata.get('author', 'None')}
            - Publication Date: {metadata.get('publication_date', 'Not found')}
            """
            
            user_prompt = f"""
            Extract and structure content from this HTML:
            {metadata_str}

            HTML: {cleaned_html[:CONFIG["max_content_length"]]}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=CONFIG["max_tokens_openai"],
                temperature=CONFIG["temperature_openai"]
            )
            
            extracted_text = response.choices[0].message.content.strip()
            
            extraction_metadata = {
                'extraction_model': 'gpt-4o-mini',
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else 0,
                'extraction_length': len(extracted_text),
                'metadata_included': metadata
            }
            
            return True, extracted_text, extraction_metadata
            
        except Exception as e:
            return False, f"OpenAI extraction failed: {str(e)}", {}
    
    def prepare_content_for_perplexity(self, extracted_text: str, max_tokens: int = CONFIG["max_tokens_perplexity"]) -> str:
        """Prepare and limit content for Perplexity analysis"""
        estimated_tokens = len(extracted_text) // 4
        
        if estimated_tokens <= max_tokens:
            return extracted_text
        
        sections = extracted_text.split('\n\n')
        priority_content = []
        metadata_section = None
        key_claims_section = None
        
        for i, section in enumerate(sections):
            if 'METADATA' in section.upper() or 'Website Domain' in section:
                metadata_section = section
            elif 'KEY CLAIMS' in section.upper() or any(section.strip().startswith(str(i)) for i in range(1, 10)):
                key_claims_section = section
        
        final_content = []
        if metadata_section:
            final_content.append(metadata_section)
        if key_claims_section:
            final_content.append(key_claims_section)
        
        current_length = sum(len(s) for s in final_content)
        for section in sections:
            if section not in [metadata_section, key_claims_section]:
                if current_length + len(section) < max_tokens * 4:
                    final_content.append(section)
                    current_length += len(section)
                else:
                    remaining_space = max_tokens * 4 - current_length
                    if remaining_space > 50:
                        final_content.append(section[:remaining_space-10] + "...")
                    break
        
        return '\n\n'.join(final_content)
    
    def analyze_with_perplexity(self, extracted_text: str) -> Tuple[bool, Dict[str, Any]]:
        """Analyze content credibility with enhanced Perplexity prompt"""
        try:
            prepared_content = self.prepare_content_for_perplexity(extracted_text)
            
            research_prompt = f"""You are a professional fact-checker analyzing web content for credibility.

            CONTENT TO VERIFY:
            {prepared_content}

            INSTRUCTIONS:
            1. Focus on metadata (domain, author, date) for credibility.
            2. Search for evidence from reliable sources (e.g., BBC, Reuters, academic papers).
            3. Verify specific claims in the KEY CLAIMS section, aiming for 3–5 claims.
            4. Assess domain reputation (e.g., known credible vs. user-generated).
            5. Evaluate author expertise or recognition.
            6. Check if publication date impacts claim relevance.

            OUTPUT:
            1. SOURCE CREDIBILITY ASSESSMENT:
               - Domain reliability (e.g., 'Highly credible', 'Unreliable')
               - Author credibility (e.g., 'Recognized journalist', 'Unknown')
               - Date relevance (e.g., 'Recent', 'Outdated')

            2. FACT VERIFICATION:
               - List each claim with status (Verified/Disputed/Unverifiable)
               - Provide supporting/contradicting sources
               - Note misleading/false info with reasons

            3. OVERALL CREDIBILITY RATING:
               - Highly Credible / Moderately Credible / Low Credibility / Not Credible
               - Explain based on domain, facts, and metadata

            4. KEY SOURCES:
               - List 2–3 sources used for verification (with URLs if possible)

            Be precise, cite sources, and ensure 3–5 claims are analyzed."""
            
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self.perplexity_api_key}"
            }
            
            data = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are a fact-checker. Analyze content for credibility, focusing on metadata."},
                    {"role": "user", "content": research_prompt}
                ],
                "temperature": CONFIG["temperature_perplexity"],
                "max_tokens": CONFIG["max_tokens_perplexity"]
            }
            
            response = requests.post(
                self.perplexity_api_url,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and result["choices"]:
                analysis_content = result["choices"][0]["message"]["content"]
                
                analysis_data = {
                    'full_analysis': analysis_content,
                    'sources': self._extract_sources_from_analysis(analysis_content),
                    'credibility_assessment': self._extract_credibility_assessment(analysis_content),
                    'metadata_assessment': self._extract_metadata_assessment(analysis_content),
                    'fact_verification': self._extract_fact_verification(analysis_content)
                }
                
                

                return True, analysis_data
            else:
                return False, {"error": "No analysis results returned"}
                
        except Exception as e:
            return False, {"error": f"Perplexity analysis failed: {str(e)}"}
    
    def _extract_metadata_assessment(self, analysis: str) -> Dict[str, str]:
        """Extract metadata-related assessments from analysis"""
        assessment = {
            'domain_credibility': 'Not assessed',
            'author_credibility': 'Not assessed',
            'date_relevance': 'Not assessed'
        }
        
        lines = analysis.lower().split('\n')
        for i, line in enumerate(lines):
            if 'domain' in line and ('credib' in line or 'reliab' in line):
                assessment['domain_credibility'] = ' '.join(lines[i:i+2]).strip()
            elif 'author' in line and ('credib' in line or 'expert' in line):
                assessment['author_credibility'] = ' '.join(lines[i:i+2]).strip()
            elif 'date' in line or 'publication' in line:
                assessment['date_relevance'] = ' '.join(lines[i:i+2]).strip()
        
        return assessment
    
    def _extract_fact_verification(self, analysis: str) -> List[Dict[str, str]]:
        """Extract fact verification results from analysis"""
        facts = []
        fact_pattern = re.compile(r'(claim|fact|statement)\s*(\d+)?\s*?:.*?(verified|disputed|false|true|unverifiable)', re.I)
        
        lines = analysis.split('\n')
        for line in lines:
            match = fact_pattern.search(line)
            if match:
                status = 'Verified' if match.group(3).lower() in ['verified', 'true'] else 'Disputed'
                facts.append({
                    'claim': line.strip(),
                    'status': status
                })
        
        return facts
    
    def _extract_sources_from_analysis(self, analysis: str) -> List[str]:
        """Extract sources mentioned in the analysis"""
        sources = []
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]*')
        found_urls = re.findall(url_pattern, analysis)
        sources.extend(found_urls)
        
        lines = analysis.split('\n')
        for line in lines:
            if 'source:' in line.lower() or 'reference:' in line.lower():
                sources.append(line.strip())
        
        return list(set(sources))
    
    def _extract_credibility_assessment(self, analysis: str) -> str:
        """Extract credibility assessment from analysis"""
        credibility_keywords = [
            'credible', 'reliable', 'accurate', 'verified', 'trustworthy',
            'false', 'misleading', 'disputed', 'controversial', 'unverifiable'
        ]
        
        assessment_lines = []
        lines = analysis.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in credibility_keywords):
                assessment_lines.append(line.strip())
        
        return ' '.join(assessment_lines) or "Assessment not clearly stated"
    
    def analyze_content(self, article_text, source_url=None):
        outputs = generate_research_outputs(article_text, source=source_url)
        
        # Save or log narrative
        print("Narrative Context:\n", outputs["narrative_context"])

        # Optional: Store to DB or write to file
        with open("structured_output.json", "w", encoding="utf-8") as f:
            json.dump(outputs["structured_granular_data"], f, indent=2)
        
        return outputs