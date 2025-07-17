# AI Movie Search Backend

AI-powered movie search with natural language query translation using TMDB API.

## Features

- Natural language to movie search query translation using AI
- TMDB API integration for comprehensive movie data
- FastAPI backend with CORS support for frontend integration
- Simple and clean movie search results

## Setup

### Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required variables:
- `OPENROUTER_API_KEY`: Your OpenRouter API key for AI query translation
- `TMDB_API_KEY`: Your TMDB API key

### Get API Keys

1. **TMDB API Key**: 
   - Go to [TMDB website](https://www.themoviedb.org/documentation/api)
   - Create an account and request an API key
   - Add it to your `.env` file

2. **OpenRouter API Key**:
   - Go to [OpenRouter website](https://openrouter.ai/)
   - Create an account and get your API key
   - Add it to your `.env` file

### Running Locally

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m app.main
```

The backend will be available at `http://localhost:3000`

## API Endpoints

- `GET /`: Web interface for testing
- `POST /api/search`: Search movies
  - Body: `{"query": "your natural language query"}`
  - Response: `{"tmdb_query": "translated query", "movies": [...], "total_count": 10, "response_time_ms": 500}`
- `GET /api/health`: Health check endpoint

## Integration

This backend is designed to work with the AI Movie Search frontend. The frontend should make requests to `/api/search` endpoint.

## Example Queries

- "Action movies from the 90s with high ratings"
- "Sci-fi films about time travel"
- "Movies starring Leonardo DiCaprio"
- "Horror films from 2020"
- "Romantic comedies with happy endings"
- "Marvel superhero movies" 