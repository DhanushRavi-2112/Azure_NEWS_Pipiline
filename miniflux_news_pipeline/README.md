# Miniflux News Pipeline

A webhook receiver and processing pipeline for Miniflux RSS reader articles.

## Setup

1. Install PostgreSQL
2. Create database: `createdb miniflux_articles`
3. Copy `.env.example` to `.env` and update values
4. Install dependencies: `pip install -r requirements.txt`
5. Initialize database: `python database/init_db.py`
6. Run server: `python run_server.py`

## API Endpoints

- `POST /webhook/miniflux` - Receive Miniflux webhook
- `GET /articles` - Get stored articles
- `GET /health` - Health check

## Features Completed

✅ PostgreSQL database setup
✅ Database schema for articles
✅ FastAPI webhook receiver
✅ JSON parsing and validation
✅ Deduplication logic
✅ Article storage with timestamps