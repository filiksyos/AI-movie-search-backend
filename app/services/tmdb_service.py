import httpx
from typing import List, Dict, Any, Optional

class TMDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p"
        
    async def search_movies(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for movies using TMDB API
        """
        
        headers = {
            "Content-Type": "application/json"
        }
        
        params = {
            "api_key": self.api_key,
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": "1"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for movies
            response = await client.get(
                f"{self.base_url}/search/movie",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            movies = data.get("results", [])
            
            # Get genre mapping for better display
            genre_map = await self._get_genre_mapping(client, headers)
            
            # Format and enrich movie data
            formatted_movies = []
            for movie in movies[:limit]:
                formatted_movie = await self._format_movie(movie, genre_map)
                formatted_movies.append(formatted_movie)
            
            return formatted_movies
    
    async def _get_genre_mapping(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[int, str]:
        """Get genre ID to name mapping"""
        try:
            response = await client.get(
                f"{self.base_url}/genre/movie/list",
                headers=headers,
                params={"api_key": self.api_key, "language": "en-US"}
            )
            response.raise_for_status()
            
            data = response.json()
            genres = data.get("genres", [])
            
            return {genre["id"]: genre["name"] for genre in genres}
        except Exception:
            return {}
    
    async def _format_movie(self, movie: Dict[str, Any], genre_map: Dict[int, str]) -> Dict[str, Any]:
        """Format movie data for frontend consumption"""
        
        # Map genre IDs to names
        genre_ids = movie.get("genre_ids", [])
        genre_names = [genre_map.get(genre_id, "") for genre_id in genre_ids if genre_id in genre_map]
        
        return {
            "id": movie.get("id"),
            "title": movie.get("title", "Unknown Title"),
            "original_title": movie.get("original_title"),
            "overview": movie.get("overview", ""),
            "release_date": movie.get("release_date", ""),
            "vote_average": round(movie.get("vote_average", 0), 1),
            "vote_count": movie.get("vote_count", 0),
            "popularity": movie.get("popularity", 0),
            "poster_path": movie.get("poster_path"),
            "backdrop_path": movie.get("backdrop_path"),
            "genre_ids": genre_ids,
            "genre_names": genre_names,
            "adult": movie.get("adult", False),
            "original_language": movie.get("original_language", ""),
            "poster_url": f"{self.image_base_url}/w500{movie.get('poster_path')}" if movie.get("poster_path") else None,
            "backdrop_url": f"{self.image_base_url}/w1280{movie.get('backdrop_path')}" if movie.get("backdrop_path") else None,
        } 