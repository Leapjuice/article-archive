# Article Archive

A self-contained Docker container that scrapes and archives articles from any URL.

## What it does

1. **Scrapes articles** - Paste any URL and it extracts the headline + article text
2. **Stores in SQLite** - Articles are saved to a local database
3. **Deduplicates** - Same URL returns the cached version instead of re-scraping
4. **Serves a beautiful UI** - Cyberpunk-themed interface matching Leapjuice Labs branding

## Quick Start

```bash
# Run the container
docker run -d -p 80:8080 leapjuice/article-archive:latest

# Or with a persistent volume for the database
docker run -d -p 80:8080 -v article-data:/app/data leapjuice/article-archive:latest
```

Then open `http://localhost` (or your domain) to use it.

## Building from source

```bash
# Clone the repo
git clone https://github.com/leapjuice/article-archive.git
cd article-archive

# Build the image
docker build -t article-archive .

# Run it
docker run -d -p 80:8080 article-archive
```

## API

```bash
# Archive an article
curl -X POST http://localhost:8080/api/archive \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

## Technical details

- **Backend:** Python Flask
- **Database:** SQLite (stored in `/app/data`)
- **Port:** 8080 (internal), maps to 80 (host)
- **No external dependencies** - completely self-contained
