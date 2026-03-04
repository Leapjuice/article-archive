import os
import sqlite3
import hashlib
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from playwright.sync_api import sync_playwright

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


def scrape_article(url):
    """
    Scrape article headline and text from a URL using Playwright.
    Returns (headline, article_text) or raises an exception.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = browser.new_page()

        try:
            # Set realistic viewport
            page.set_viewport_size({"width": 1920, "height": 1080})

            # Navigate with timeout
            response = page.goto(url, timeout=30000, wait_until="domcontentloaded")

            if response is None:
                raise ValueError("Could not load page")

            # Wait a bit for dynamic content
            page.wait_for_timeout(2000)

            # Try to find headline
            headline = None

            # Try Open Graph title
            try:
                og_title = page.get_attribute('meta[property="og:title"]', 'content', timeout=5000)
                if og_title:
                    headline = og_title
            except:
                pass

            # Try Twitter title
            if not headline:
                try:
                    twitter_title = page.get_attribute('meta[name="twitter:title"]', 'content', timeout=5000)
                    if twitter_title:
                        headline = twitter_title
                except:
                    pass

            # Try article h1
            if not headline:
                try:
                    article_elem = page.query_selector('article')
                    if article_elem:
                        h1 = article_elem.query_selector('h1')
                        if h1:
                            headline = h1.inner_text()
                except:
                    pass

            # Try h1 tag
            if not headline:
                try:
                    h1 = page.query_selector('h1')
                    if h1:
                        headline = h1.inner_text()
                except:
                    pass

            # Fall back to title tag
            if not headline:
                title = page.title()
                if title:
                    headline = title

            if not headline:
                raise ValueError("Could not extract headline from article")

            # Try to find article text
            article_text = ""

            # Try article tag
            try:
                article_elem = page.query_selector('article')
                if article_elem:
                    paragraphs = article_elem.query_selector_all('p')
                    texts = []
                    for p in paragraphs:
                        text = p.inner_text()
                        if text and len(text.strip()) > 20:  # Filter short texts
                            texts.append(text.strip())
                    article_text = '\n\n'.join(texts)
            except:
                pass

            # Try main tag
            if not article_text:
                try:
                    main_elem = page.query_selector('main')
                    if main_elem:
                        paragraphs = main_elem.query_selector_all('p')
                        texts = []
                        for p in paragraphs:
                            text = p.inner_text()
                            if text and len(text.strip()) > 20:
                                texts.append(text.strip())
                        article_text = '\n\n'.join(texts)
                except:
                    pass

            # Try common article class names
            if not article_text:
                class_names = ['article-content', 'article-body', 'post-content', 'entry-content', 'content', 'story-body']
                for class_name in class_names:
                    try:
                        elem = page.query_selector(f'.{class_name}')
                        if elem:
                            paragraphs = elem.query_selector_all('p')
                            texts = []
                            for p in paragraphs:
                                text = p.inner_text()
                                if text and len(text.strip()) > 20:
                                    texts.append(text.strip())
                            if texts:
                                article_text = '\n\n'.join(texts)
                                break
                    except:
                        continue

            # Last resort: get all paragraphs
            if not article_text:
                try:
                    paragraphs = page.query_selector_all('p')
                    texts = []
                    for p in paragraphs:
                        text = p.inner_text()
                        if text and len(text.strip()) > 20:
                            texts.append(text.strip())
                    article_text = '\n\n'.join(texts)
                except:
                    pass

            if not article_text:
                raise ValueError("Could not extract article text from page")

            return headline.strip(), article_text.strip()

        finally:
            browser.close()


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

    url_hash = hashlib.sha256(url.encode()).hexdigest()

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
