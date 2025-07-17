import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

from app.services.query_translator import QueryTranslator
from app.services.tmdb_service import TMDBService

load_dotenv()

app = FastAPI(title="AI Movie Search Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite default port
        "http://localhost:4173",      # Vite preview port
        "http://localhost:8080",      # Custom frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Movie Search Assistant</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .container {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            textarea {
                width: 100%;
                height: 100px;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
            button {
                background-color: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover {
                background-color: #0056b3;
            }
            .result {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                padding: 15px;
                margin-top: 10px;
            }
            .movie {
                border-bottom: 1px solid #e9ecef;
                padding-bottom: 10px;
                margin-bottom: 10px;
                display: flex;
                gap: 15px;
            }
            .movie:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }
            .movie-poster {
                width: 60px;
                height: 90px;
                object-fit: cover;
                border-radius: 5px;
            }
            .movie-info {
                flex: 1;
            }
            .movie-title {
                font-weight: bold;
                color: #007bff;
                margin-bottom: 5px;
            }
            .movie-meta {
                color: #666;
                font-size: 14px;
                margin-bottom: 5px;
            }
            .movie-overview {
                color: #333;
                font-size: 14px;
                line-height: 1.4;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 AI Movie Search Assistant</h1>
            
            <div>
                <label for="searchQuery">What movies would you like to find?</label>
                <textarea 
                    id="searchQuery" 
                    placeholder="e.g., Action movies from the 90s with high ratings, or Sci-fi films with time travel"
                ></textarea>
                <button onclick="searchMovies()">🔍 Search Movies</button>
            </div>
            
            <div id="result"></div>
        </div>

        <script>
            async function searchMovies() {
                const query = document.getElementById('searchQuery').value;
                const resultDiv = document.getElementById('result');
                
                if (!query.trim()) {
                    alert('Please enter a search query');
                    return;
                }
                
                resultDiv.innerHTML = '<p>🔍 Searching movies...</p>';
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: query })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    resultDiv.innerHTML = `<div class="result"><p>❌ Error: ${error.message}</p></div>`;
                }
            }
            
            function displayResults(data) {
                const resultDiv = document.getElementById('result');
                
                if (!data.movies || data.movies.length === 0) {
                    resultDiv.innerHTML = '<div class="result"><p>No movies found.</p></div>';
                    return;
                }
                
                let html = '<div class="result">';
                html += `<h3>🔍 Search Type: <code>${data.search_params.search_type}</code></h3>`;
                html += `<h4>📋 Parameters: <code>${JSON.stringify(data.search_params.params)}</code></h4>`;
                html += `<p>Found ${data.movies.length} movies:</p>`;
                
                data.movies.forEach(movie => {
                    const posterUrl = movie.poster_path ? 
                        `https://image.tmdb.org/t/p/w92${movie.poster_path}` : 
                        'https://via.placeholder.com/60x90?text=No+Image';
                    
                    html += `
                        <div class="movie">
                            <img src="${posterUrl}" alt="${movie.title}" class="movie-poster">
                            <div class="movie-info">
                                <div class="movie-title">${movie.title}</div>
                                <div class="movie-meta">
                                    ⭐ ${movie.vote_average}/10 | 
                                    📅 ${movie.release_date || 'Unknown'} | 
                                    🎭 ${movie.genre_names ? movie.genre_names.join(', ') : 'Unknown'}
                                </div>
                                <div class="movie-overview">${movie.overview || 'No description available'}</div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                resultDiv.innerHTML = html;
            }
            
            // Allow Enter key to trigger search
            document.getElementById('searchQuery').addEventListener('keypress', function(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    searchMovies();
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/api/search")
async def search_movies(query: SearchQuery):
    start_time = time.time()
    
    # Get API keys from environment
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    tmdb_api_key = os.getenv("TMDB_API_KEY")
    
    if not openrouter_api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    if not tmdb_api_key:
        raise HTTPException(status_code=500, detail="TMDB API key not configured")
    
    try:
        # Initialize services
        translator = QueryTranslator(openrouter_api_key)
        tmdb = TMDBService(tmdb_api_key)
        
        # Translate natural language to TMDB search parameters
        search_params = await translator.translate_query(query.query)
        
        # Search movies using TMDB API
        movies = await tmdb.search_movies(search_params)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "search_params": search_params,
            "movies": movies,
            "total_count": len(movies),
            "response_time_ms": response_time_ms
        }
        
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "AI Movie Search Assistant API is running",
        "tmdb_configured": os.getenv("TMDB_API_KEY") is not None,
        "openrouter_configured": os.getenv("OPENROUTER_API_KEY") is not None
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port) 