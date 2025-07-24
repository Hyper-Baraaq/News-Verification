import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import CONFIG
import json

class DatabaseManager:
    def __init__(self, db_path: str = CONFIG.get("db_path", "cache.db")):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        # Ensure optional columns in domain_credibility
        for col, col_type in [
            ("category", "TEXT"),
            ("source_type", "TEXT"),
            ("bias_level", "TEXT"),
            ("reliability", "TEXT")
        ]:
            self.ensure_column_exists("domain_credibility", col, col_type)

    def create_tables(self):
        cursor = self.conn.cursor()
        # domain_credibility core
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS domain_credibility (
                domain TEXT PRIMARY KEY,
                trust_score REAL
            )
            """
        )
        # url_verification_cache core
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS url_verification_cache (
                original_url TEXT PRIMARY KEY,
                url_hash TEXT,
                domain TEXT,
                title TEXT,
                author TEXT,
                publication_date TEXT,
                content_type TEXT,
                content_length INTEGER,
                confidence_score REAL,
                confidence_level TEXT,
                source_credibility_score REAL,
                content_consistency_score REAL,
                verification_coverage_score REAL,
                extracted_text TEXT,
                credibility_assessment TEXT,
                fact_verification_results TEXT,
                sources_used TEXT,
                full_perplexity_analysis TEXT,
                metadata_assessment TEXT,
                processing_time_seconds REAL,
                openai_tokens_used INTEGER,
                perplexity_calls_made INTEGER,
                extraction_model TEXT,
                first_verified_at TEXT,
                last_accessed_at TEXT,
                access_count INTEGER DEFAULT 1,
                expires_at TEXT,
                cache_status TEXT
            )
            """
        )
        self.conn.commit()

    def ensure_column_exists(self, table_name: str, column_name: str, column_type: str = "TEXT"):
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing = [row[1] for row in cursor.fetchall()]
        if column_name not in existing:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            self.conn.commit()

    def get_cached_result(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch cached verification result by exact full URL match"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM url_verification_cache
                WHERE original_url = ? AND cache_status IN ('fresh', 'stale')
                """,
                (url,)
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
                    WHERE original_url = ?
                    """,
                    (datetime.now(), url)
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
            cursor = self.conn.cursor()
            url = result['url']
            url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
            expires_at = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            fact_results = json.dumps(result.get('fact_verification', []))
            sources = json.dumps(result.get('sources', []))
            metadata = json.dumps(result.get('metadata_assessment', {}))
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(original_url) DO UPDATE SET
                    confidence_score = excluded.confidence_score,
                    confidence_level = excluded.confidence_level,
                    extracted_text = excluded.extracted_text,
                    credibility_assessment = excluded.credibility_assessment,
                    fact_verification_results = excluded.fact_verification_results,
                    sources_used = excluded.sources_used,
                    metadata_assessment = excluded.metadata_assessment,
                    last_accessed_at = excluded.last_accessed_at,
                    access_count = access_count + 1,
                    expires_at = excluded.expires_at,
                    cache_status = excluded.cache_status
                """,
                (
                    url, url_hash, result.get('domain', ''), result.get('title'), result.get('author'), result.get('publication_date'),
                    result.get('content_type'), result.get('content_length', 0), result['confidence_score'], result['confidence_level'],
                    result['score_components'].get('source_credibility', 0.0), result['score_components'].get('content_consistency', 0.0), result['score_components'].get('verification_coverage', 0.0),
                    result.get('extracted_text'), result.get('credibility_assessment'), fact_results, sources, result.get('full_analysis', ''), metadata,
                    processing_time, result.get('openai_tokens_used', 0), result.get('perplexity_calls_made', 1), result.get('extraction_model', 'gpt-4o-mini'),
                    result.get('first_verified_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1, expires_at, 'fresh'
                )
            )
            self.conn.commit()
        except Exception as e:
            print(f"Cache insert error: {e}")

    def get_trust_score_from_db(self, key: str, use_full_url: bool = False) -> Optional[float]:
        cursor = self.conn.cursor()
        if use_full_url:
            cursor.execute("SELECT confidence_score FROM url_verification_cache WHERE original_url = ?", (key,))
        else:
            cursor.execute("SELECT trust_score FROM domain_credibility WHERE domain = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def insert_domain(self, domain: str, trust_score: float, category: str, source_type: str, bias_level: str, reliability: str, notes: str):
        """Insert or update a domain in the domain_credibility table"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO domain_credibility (
                    domain, trust_score, category, source_type, bias_level, reliability, notes,
                    created_at, updated_at, last_checked, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    trust_score = excluded.trust_score,
                    category = excluded.category,
                    source_type = excluded.source_type,
                    bias_level = excluded.bias_level,
                    reliability = excluded.reliability,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at,
                    last_checked = excluded.last_checked
                """,
                (
                    domain, trust_score, category, source_type, bias_level, reliability, notes,
                    now, now, now, 1
                )
            )
            self.conn.commit()
        except Exception as e:
            print(f"Domain insert error: {e}")

    def close(self):
        self.conn.close()
