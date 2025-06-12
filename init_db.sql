-- ===============================================
-- TABLE 1: DOMAIN_CREDIBILITY - External Website Trust Database
-- ===============================================
CREATE TABLE IF NOT EXISTS domain_credibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain VARCHAR(255) UNIQUE NOT NULL,
    trust_score DECIMAL(4,3) NOT NULL CHECK (trust_score >= 0.000 AND trust_score <= 1.000),
    
    -- Basic Classification
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    source_type TEXT CHECK(source_type IN ('news', 'blog', 'academic', 'government', 'social_media', 'commercial', 'fact_checker', 'unknown')) DEFAULT 'unknown',
    
    -- Credibility Indicators
    bias_level TEXT CHECK(bias_level IN ('low', 'medium', 'high', 'unknown')) DEFAULT 'unknown',
    reliability TEXT CHECK(reliability IN ('very_high', 'high', 'medium', 'low', 'very_low', 'unknown')) DEFAULT 'unknown',
    
    -- Additional Context
    country_code VARCHAR(3),
    language VARCHAR(5) DEFAULT 'en',
    notes TEXT,
    verification_source VARCHAR(255),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_domain ON domain_credibility (domain);
CREATE INDEX IF NOT EXISTS idx_trust_score ON domain_credibility (trust_score);
CREATE INDEX IF NOT EXISTS idx_source_type ON domain_credibility (source_type);
CREATE INDEX IF NOT EXISTS idx_active ON domain_credibility (is_active);

-- ===============================================
-- TABLE 2: URL_VERIFICATION_CACHE - Complete Results Storage
-- ===============================================
CREATE TABLE IF NOT EXISTS url_verification_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- URL Information
    original_url VARCHAR(2048) NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    domain VARCHAR(255) NOT NULL,
    
    -- Content Metadata
    title TEXT,
    author VARCHAR(500),
    publication_date DATE,
    content_type VARCHAR(50),
    content_length INTEGER,
    
    -- CORE VERIFICATION RESULTS
    confidence_score DECIMAL(6,4) NOT NULL CHECK (confidence_score >= 0.0000 AND confidence_score <= 1.0000),
    confidence_level TEXT CHECK(confidence_level IN ('high', 'medium', 'low')) NOT NULL,
    
    -- Score Breakdown
    source_credibility_score DECIMAL(6,4),
    content_consistency_score DECIMAL(6,4),
    verification_coverage_score DECIMAL(6,4),
    
    -- Analysis Results
    extracted_text LONGTEXT,
    credibility_assessment TEXT,
    fact_verification_results TEXT,
    sources_used TEXT,
    full_perplexity_analysis LONGTEXT,
    metadata_assessment TEXT,
    
    -- Processing Information
    processing_time_seconds DECIMAL(6,2),
    openai_tokens_used INTEGER DEFAULT 0,
    perplexity_calls_made INTEGER DEFAULT 0,
    extraction_model VARCHAR(50) DEFAULT 'gpt-4o-mini',
    
    -- Cache Management
    first_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    cache_status TEXT CHECK(cache_status IN ('fresh', 'stale', 'expired', 'processing', 'failed')) DEFAULT 'fresh'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_url_hash ON url_verification_cache (url_hash);
CREATE INDEX IF NOT EXISTS idx_domain ON url_verification_cache (domain);
CREATE INDEX IF NOT EXISTS idx_confidence_score ON url_verification_cache (confidence_score);
CREATE INDEX IF NOT EXISTS idx_cache_status ON url_verification_cache (cache_status);
CREATE INDEX IF NOT EXISTS idx_expires_at ON url_verification_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_last_accessed ON url_verification_cache (last_accessed_at);