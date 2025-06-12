import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import CONFIG
import json

class DatabaseManager:
    """Class to manage SQLite database interactions for domain trust scores and URL verification cache"""

    def __init__(self):
        self.db_path = CONFIG["db_path"]
        self.initialize_database()
        self.seed_database()

    def initialize_database(self):
        """Initialize the database with the required schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read and execute the SQL schema
            with open('init_db.sql', 'r') as f:
                schema_sql = f.read()
            cursor.executescript(schema_sql)
            
            conn.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")
        finally:
            conn.close()

    def seed_database(self):
        """Seed the database with sample data if tables are empty"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if domain_credibility is empty
            cursor.execute("SELECT COUNT(*) FROM domain_credibility")
            if cursor.fetchone()[0] == 0:
                cursor.executescript("""
                    INSERT INTO domain_credibility (
                        domain, trust_score, category, source_type, bias_level, reliability, country_code, language, notes, verification_source, created_at, updated_at, last_checked, is_active
                    ) VALUES
                        ('nytimes.com', 0.980, 'news', 'news', 'low', 'high', 'US', 'en', 'Highly reputable news outlet', 'Media Bias/Fact Check', '2025-06-12 18:37:00', '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1),
                        ('bbc.com', 0.980, 'news', 'news', 'low', 'high', 'UK', 'en', 'Trusted global news source', 'Media Bias/Fact Check', '2025-06-12 18:37:00', '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1),
                        ('infowars.com', 0.050, 'news', 'news', 'high', 'very_low', 'US', 'en', 'Known for misinformation', 'Media Bias/Fact Check', '2025-06-12 18:37:00', '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1),
                        ('wikipedia.org', 0.850, 'reference', 'academic', 'medium', 'high', 'US', 'en', 'Crowdsourced but generally reliable', 'Internal analysis', '2025-06-12 18:37:00', '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1),
                        ('blogspot.com', 0.150, 'blog', 'blog', 'unknown', 'low', 'US', 'en', 'User-generated, varies widely', 'Internal analysis', '2025-06-12 18:37:00', '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1);
                """)
            
            # Check if url_verification_cache is empty
            cursor.execute("SELECT COUNT(*) FROM url_verification_cache")
            if cursor.fetchone()[0] == 0:
                # Compute URL hashes dynamically
                url1 = 'https://www.bbc.com/news/world-us-canada-12345678'
                url2 = 'https://www.infowars.com/post/conspiracy-claim'
                hash1 = hashlib.sha256(url1.encode('utf-8')).hexdigest()
                hash2 = hashlib.sha256(url2.encode('utf-8')).hexdigest()
                
                cursor.executescript(f"""
                    INSERT INTO url_verification_cache (
                        original_url, url_hash, domain, title, author, publication_date, content_type, content_length,
                        confidence_score, confidence_level, source_credibility_score, content_consistency_score, verification_coverage_score,
                        extracted_text, credibility_assessment, fact_verification_results, sources_used, full_perplexity_analysis, metadata_assessment,
                        processing_time_seconds, openai_tokens_used, perplexity_calls_made, extraction_model,
                        first_verified_at, last_accessed_at, access_count, expires_at, cache_status
                    ) VALUES
                        (
                            '{url1}', '{hash1}', 'bbc.com', 'US Election Results 2024', 'BBC News Team', '2024-11-05', 'article', 5000,
                            0.9200, 'high', 0.9800, 0.9500, 0.9000,
                            'METADATA SECTION\nWebsite Domain: bbc.com\nKEY CLAIMS\n1. Election held on Nov 5...\n',
                            'Highly credible, verified by multiple sources',
                            '[{{ "claim": "Election held on Nov 5", "status": "Verified" }}]',
                            '["https://www.reuters.com", "https://www.apnews.com"]',
                            'Perplexity analysis: BBC article is reliable...',
                            '{{"domain_credibility": "high", "author_credibility": "high", "date_relevance": "recent"}}',
                            12.50, 15000, 1, 'gpt-4o-mini',
                            '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1, '2025-07-12 18:37:00', 'fresh'
                        ),
                        (
                            '{url2}', '{hash2}', 'infowars.com', 'Secret Government Plan Exposed', 'Alex Jones', '2025-06-10', 'article', 3000,
                            0.1000, 'low', 0.0500, 0.2000, 0.3000,
                            'METADATA SECTION\nWebsite Domain: infowars.com\nKEY CLAIMS\n1. Govt conspiracy...\n',
                            'Low credibility, contains unverified claims',
                            '[{{ "claim": "Govt conspiracy", "status": "Disputed" }}]',
                            '["https://unknownblog.com"]',
                            'Perplexity analysis: InfoWars claims lack evidence...',
                            '{{"domain_credibility": "low", "author_credibility": "low", "date_relevance": "recent"}}',
                            8.75, 10000, 1, 'gpt-4o-mini',
                            '2025-06-12 18:37:00', '2025-06-12 18:37:00', 1, '2025-07-12 18:37:00', 'fresh'
                        );
                """)
            
            conn.commit()
        except Exception as e:
            print(f"Database seeding error: {e}")
        finally:
            conn.close()

    def get_trust_score_from_db(self, domain: str) -> Optional[float]:
        """Fetch trust score from the domain_credibility table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT trust_score FROM domain_credibility WHERE domain = ? AND is_active = 1", (domain,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            return None

    def insert_domain(self, domain: str, trust_score: float, category: str, bias_level: str, reliability: str, notes: str):
        """Insert or update a domain in the domain_credibility table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Validate inputs
            bias_level = bias_level if bias_level in ['low', 'medium', 'high', 'unknown'] else 'unknown'
            reliability = reliability if reliability in ['very_high', 'high', 'medium', 'low', 'very_low', 'unknown'] else 'unknown'
            category = category if category else 'general'
            
            cursor.execute(
                """
                INSERT INTO domain_credibility (
                    domain, trust_score, category, source_type, bias_level, reliability, notes,
                    created_at, updated_at, last_checked, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    trust_score = excluded.trust_score,
                    category = excluded.category,
                    bias_level = excluded.bias_level,
                    reliability = excluded.reliability,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at,
                    last_checked = excluded.last_checked
                """,
                (
                    domain, trust_score, category, 'unknown', bias_level, reliability, notes,
                    datetime.now(), datetime.now(), datetime.now(), 1
                )
            )
            conn.commit()
        except Exception as e:
            print(f"Domain insert error: {e}")
        finally:
            conn.close()

    def get_cached_result(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch cached verification result by URL hash"""
        try:
            url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM url_verification_cache
                WHERE url_hash = ? AND cache_status IN ('fresh', 'stale')
                """,
                (url_hash,)
            )
            result = cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in cursor.description]
                result_dict = dict(zip(columns, result))
                
                # Update access count and last accessed time
                cursor.execute(
                    """
                    UPDATE url_verification_cache
                    SET access_count = access_count + 1,
                        last_accessed_at = ?,
                        cache_status = 'fresh'
                    WHERE url_hash = ?
                    """,
                    (datetime.now(), url_hash)
                )
                conn.commit()
                
                # Parse JSON fields
                for field in ['fact_verification_results', 'sources_used', 'metadata_assessment']:
                    if result_dict.get(field):
                        result_dict[field] = json.loads(result_dict[field])
                
                return result_dict
            
            return None
        except Exception as e:
            print(f"Cache retrieval error: {e}")
            return None
        finally:
            conn.close()

    def insert_cached_result(self, result: Dict[str, Any], processing_time: float):
        """Insert or update a verification result in the url_verification_cache table"""
        try:
            url_hash = hashlib.sha256(result['url'].encode('utf-8')).hexdigest()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prepare JSON fields
            fact_verification_results = json.dumps(result.get('fact_verification', []))
            sources_used = json.dumps(result.get('sources', []))
            metadata_assessment = json.dumps(result.get('metadata_assessment', {}))
            
            # Calculate expires_at (e.g., 30 days from now)
            expires_at = datetime.now() + timedelta(days=30)
            
            cursor.execute(
                """
                INSERT INTO url_verification_cache (
                    original_url, url_hash, domain, title, author, publication_date,
                    content_type, content_length, confidence_score, confidence_level,
                    source_credibility_score, content_consistency_score, verification_coverage_score,
                    extracted_text, credibility_assessment, fact_verification_results,
                    sources_used, full_perplexity_analysis, metadata_assessment,
                    processing_time_seconds, openai_tokens_used, perplexity_calls_made,
                    extraction_model, first_verified_at, last_accessed_at, access_count,
                    expires_at, cache_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url_hash) DO UPDATE SET
                    original_url = excluded.original_url,
                    domain = excluded.domain,
                    title = excluded.title,
                    confidence_score = excluded.confidence_score,
                    confidence_level = excluded.confidence_level,
                    extracted_text = excluded.extracted_text,
                    credibility_assessment = excluded.credibility_assessment,
                    fact_verification_results = excluded.fact_verification_results,
                    sources_used = excluded.sources_used,
                    full_perplexity_analysis = excluded.full_perplexity_analysis,
                    metadata_assessment = excluded.metadata_assessment,
                    last_accessed_at = excluded.last_accessed_at,
                    access_count = access_count + 1,
                    expires_at = excluded.expires_at,
                    cache_status = excluded.cache_status
                """,
                (
                    result['url'], url_hash, result.get('domain', ''),
                    result.get('title'), result.get('author'), result.get('publication_date'),
                    result.get('content_type'), result.get('content_length', 0),
                    result['confidence_score'], result['confidence_level'].split('(')[0].strip().split()[-1].lower(),
                    result['score_components'].get('source_credibility', 0.0),
                    result['score_components'].get('content_consistency', 0.0),
                    result['score_components'].get('verification_coverage', 0.0),
                    result.get('extracted_text'), result.get('credibility_assessment'),
                    fact_verification_results, sources_used, result.get('full_analysis'),
                    metadata_assessment, processing_time,
                    result.get('openai_tokens_used', 0), result.get('perplexity_calls_made', 1),
                    result.get('extraction_model', 'gpt-4o-mini'), datetime.now(), datetime.now(),
                    1, expires_at, 'fresh'
                )
            )
            conn.commit()
        except Exception as e:
            print(f"Cache insert error: {e}")
        finally:
            conn.close()