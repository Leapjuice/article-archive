# Article Archive

A self-contained Docker container that scrapes and archives articles from any URL using a headless browser (Playwright). Features a cyberpunk-themed UI for archiving and browsing articles.

## Features

- **Headless Browser Scraping** - Uses Playwright/Chromium to render pages like a real browser
- **Paywall Bypass** - Falls back to Jina.ai text extraction for paywalled sites (WSJ, NYT, Bloomberg)
- **Article Database** - SQLite database stores all archived articles
- **Deduplication** - Same URL returns cached version automatically
- **Search** - Search through archived articles by headline or content
- **Beautiful UI** - Cyberpunk-themed interface matching Leapjuice Labs branding

## Supported Sites

Works great with:
- CNBC
- BBC
- News sites with standard paywalls
- Most public articles

Limited support for:
- Hard paywalled sites (WSJ, NYT) - may work via Jina.ai fallback

## Quick Start

### Prerequisites
- Docker installed
- Port 80 available (or map to any port)

### Run the Container

```bash
# Basic run (database will reset on container restart)
docker run -d -p 80:8080 --name article-archive leapjuice/article-archive:latest

# With persistent database (recommended)
docker volume create article-data
docker run -d -p 80:8080 -v article-data:/app/data --name article-archive leapjuice/article-archive:latest
```

Then open http://localhost (or your server IP/domain)

## Building from Source

```bash
# Clone the repository
git clone https://github.com/Leapjuice/article-archive.git
cd article-archive

# Build the image
docker build -t article-archive .

# Run it
docker run -d -p 80:8080 article-archive
```

## Usage

1. **Archive an Article**
   - Paste any URL in the input box
   - Click "ARCHIVE"
   - Wait for the article to be scraped and displayed

2. **View Archived Articles**
   - Recent articles appear on the home page
   - Use the search box to filter
   - Click "VIEW ALL" to see all archived articles

3. **Clear/New Article**
   - Click "CLEAR / NEW ARTICLE" to reset and archive another

## API

```bash
# Archive an article
curl -X POST http://localhost:8080/api/archive \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'

# Get specific article
curl http://localhost:8080/api/article/<url_hash>

# Get all articles
curl http://localhost:8080/api/articles
```

## Technical Details

- **Backend:** Python Flask
- **Scraper:** Playwright (headless Chromium browser)
- **Database:** SQLite (stored in `/app/data`)
- **Port:** 8080 (internal), map to desired host port
- **No external dependencies** - completely self-contained

## Troubleshooting

### Container won't start
- Make sure port 80 (or your mapped port) isn't already in use
- Check Docker is running: `docker ps`

### Scraping fails
- Some sites block automated access (especially hard paywalls like WSJ)
- Try a different URL
- Check container logs: `docker logs article-archive`

### Can't access from browser
- Check firewall: `sudo ufw allow 80/tcp`
- Check container is running: `docker ps`

## Docker Hub

Pre-built image available:
```
docker pull leapjuice/article-archive:latest
```

## GitHub

Source code: https://github.com/Leapjuice/article-archive

## License

MIT
