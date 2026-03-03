import os
import sqlite3
import hashlib
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from bs4 import BeautifulSoup

app = Flask(__name__)

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'archive.db')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def init_db():
    """Initialize the database with the articles table."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            url_hash TEXT UNIQUE NOT NULL,
            headline TEXT NOT NULL,
            article_text TEXT NOT NULL,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def get_url_hash(url):
    """Generate a SHA256 hash for the URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def scrape_article(url):
    """
    Scrape article headline and text from a URL.
    Returns (headline, article_text) or raises an exception.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'lxml')

    # Try to find headline
    headline = None

    # Try Open Graph title first
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        headline = og_title['content']

    # Try Twitter title
    if not headline:
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            headline = twitter_title['content']

    # Try article tag
    if not headline:
        article_h1 = soup.find('article')
        if article_h1:
            h1 = article_h1.find('h1')
            if h1:
                headline = h1.get_text(strip=True)

    # Try h1 tag
    if not headline:
        h1 = soup.find('h1')
        if h1:
            headline = h1.get_text(strip=True)

    # Fall back to title tag
    if not headline:
        title = soup.find('title')
        if title:
            headline = title.get_text(strip=True)

    if not headline:
        raise ValueError("Could not extract headline from article")

    # Try to find article text
    article_text = ""

    # Try article tag
    article_elem = soup.find('article')
    if article_elem:
        # Get all paragraphs within article
        paragraphs = article_elem.find_all('p')
        article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    # Try main tag
    if not article_text:
        main_elem = soup.find('main')
        if main_elem:
            paragraphs = main_elem.find_all('p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    # Try common article class names
    if not article_text:
        for class_name in ['article-content', 'article-body', 'post-content', 'entry-content', 'content']:
            elem = soup.find(class_=class_name)
            if elem:
                paragraphs = elem.find_all('p')
                article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if article_text:
                    break

    # Last resort: get all paragraphs from body
    if not article_text:
        body = soup.find('body')
        if body:
            paragraphs = body.find_all('p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    if not article_text:
        raise ValueError("Could not extract article text from page")

    return headline.strip(), article_text.strip()


@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory(os.path.dirname(__file__), 'page.html')


@app.route('/page.html')
def page():
    """Serve the archive page."""
    return send_from_directory(os.path.dirname(__file__), 'page.html')


@app.route('/api/archive', methods=['POST'])
def archive_article():
    """Archive an article from a URL."""
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    url = data['url'].strip()

    # Validate URL
    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL. Must start with http:// or https://'}), 400

    url_hash = get_url_hash(url)

    # Check if already archived
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id, headline, article_text, archived_at FROM articles WHERE url_hash = ?', (url_hash,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return jsonify({
            'id': existing[0],
            'headline': existing[1],
            'article_text': existing[2],
            'archived_at': existing[3],
            'cached': True
        })

    # Scrape the article
    try:
        headline, article_text = scrape_article(url)
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to scrape article: {str(e)}'}), 500

    # Store in database
    try:
        cursor.execute(
            'INSERT INTO articles (url, url_hash, headline, article_text) VALUES (?, ?, ?, ?)',
            (url, url_hash, headline, article_text)
        )
        article_id = cursor.lastrowid
        archived_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.commit()
        conn.close()

        return jsonify({
            'id': article_id,
            'url': url,
            'url_hash': url_hash,
            'headline': headline,
            'article_text': article_text,
            'archived_at': archived_at,
            'cached': False
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to save article: {str(e)}'}), 500


@app.route('/api/article/<url_hash>', methods=['GET'])
def get_article(url_hash):
    """Retrieve an archived article by its URL hash."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        'SELECT id, url, headline, article_text, archived_at FROM articles WHERE url_hash = ?',
        (url_hash,)
    )
    article = cursor.fetchone()
    conn.close()

    if not article:
        return jsonify({'error': 'Article not found'}), 404

    return jsonify({
        'id': article[0],
        'url': article[1],
        'headline': article[2],
        'article_text': article[3],
        'archived_at': article[4]
    })


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=False)
