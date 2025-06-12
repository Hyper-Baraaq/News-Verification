import sqlite3
from datetime import datetime

def create_db(db_path='domain_trust_db.sqlite3'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS domains (
            domain TEXT PRIMARY KEY,
            trust_score REAL,
            category TEXT,
            bias_level TEXT CHECK(bias_level IN ('low', 'medium', 'high')) DEFAULT 'medium',
            reliability TEXT CHECK(reliability IN ('low', 'medium', 'high')) DEFAULT 'medium',
            notes TEXT,
            last_updated TEXT,
            active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    insert_sample_domains(conn)
    conn.close()
    print(f"Database initialized at {db_path}")

def insert_sample_domains(conn):
    cursor = conn.cursor()
    domains = [
        ('reuters.com', 0.92, 'news', 'low', 'high', 'International news agency with strong fact-checking standards and editorial oversight', '2025-06-10 10:00:00', 1),
        ('facebook.com', 0.75, 'social media', 'medium', 'medium', 'Social media platform with user-generated content, limited editorial oversight', '2025-06-10 09:45:00', 1),
        ('nature.com', 0.95, 'academic', 'low', 'high', 'Peer-reviewed scientific journal with rigorous editorial process', '2025-06-10 11:00:00', 1),
        ('medium.com', 0.55, 'blog', 'medium', 'medium', 'User publishing platform with varied content quality and editorial standards', '2025-06-10 11:00:00', 1),
        ('breitbart.com', 0.25, 'news', 'high', 'low', 'Opinion-heavy political content with documented bias and accuracy issues', '2025-06-10 12:00:00', 1),
        ('bbc.com', 0.88, 'news', 'low', 'high', 'British broadcaster with strong editorial standards and global coverage', '2025-06-10 12:00:00', 1),
        ('twitter.com', 0.30, 'social media', 'high', 'medium', 'Microblogging platform with real-time content, limited fact-checking', '2025-06-10 09:30:00', 1),
        ('cdc.gov', 0.98, 'government', 'low', 'high', 'U.S. Centers for Disease Control - authoritative health information', '2025-06-10 07:50:00', 1),
        ('reddit.com', 0.45, 'social media', 'medium', 'medium', 'Discussion platform with community moderation, quality varies by subreddit', '2025-06-10 03:00:00', 1),
        ('infowars.com', 0.10, 'blog', 'high', 'low', 'Conspiracy theory website with documented misinformation', '2025-06-10 14:00:00', 0),
        ('nytimes.com', 0.92, 'news', 'medium', 'high', 'Major newspaper with investigative journalism and editorial standards', '2025-06-10 04:50:00', 1),
        ('wsj.com', 0.85, 'news', 'medium', 'high', 'Financial newspaper with strong business reporting and editorial rigor', '2025-06-10 09:00:00', 1)
    ]
    for d in domains:
        cursor.execute('''
            INSERT OR REPLACE INTO domains (domain, trust_score, category, bias_level, reliability, notes, last_updated, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', d)
    conn.commit()

if __name__ == '__main__':
    create_db() 