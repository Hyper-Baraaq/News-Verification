import os

# Configuration dictionary for all settings
CONFIG = {
    # API settings
    "openai_api_key": os.getenv("OPENAI_API_KEY", "abc"),
    "perplexity_api_key": os.getenv("PERPLEXITY_API_KEY", "xyz"),
    "perplexity_api_url": "https://api.perplexity.ai/chat/completions",

    # Database settings
    "db_path": os.getenv("DB_PATH", "domain_trust_db.sqlite3"),

    # Source credibility settings
    "trusted_domains": {
        "nytimes.com": 0.98,
        "bbc.com": 0.98,
        "reuters.com": 0.95,
        "washingtonpost.com": 0.95,
        "theguardian.com": 0.95,
        "apnews.com": 0.90,
        "npr.org": 0.90,
        "cnn.com": 0.85,
        "aljazeera.com": 0.85
    },
    "untrusted_domains": {
        "example.com": 0.05,
        "blogspot.com": 0.15,
        "wordpress.com": 0.15,
        "medium.com": 0.2,
        "infowars.com": 0.05,
        "breitbart.com": 0.1
    },
    "default_domain_score": 0.35,

    # Content analysis settings
    "max_tokens_openai": 15000,
    "max_tokens_perplexity": 2000,
    "temperature_openai": 0.2,
    "temperature_perplexity": 0.2,
    "max_content_length": 500000,

    # Sensitive topics for confidence calculation
    "sensitive_topics": [
        "politics", "health", "science", "election",
        "vaccine", "climate", "war", "conflict"
    ],

    # Confidence score weights
    "confidence_weights": {
        "trusted": {
            "source_credibility": 0.4,
            "content_consistency": 0.5,
            "verification_coverage": 0.1
        },
        "default": {
            "source_credibility": 0.35,
            "content_consistency": 0.45,
            "verification_coverage": 0.2
        },
        "sensitive_adjustments": {
            "content_consistency": 0.05,
            "verification_coverage": -0.05
        }
    }
}
