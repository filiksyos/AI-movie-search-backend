import httpx
from typing import List, Dict, Any, Optional

class TMDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p"
        
    async def search_movies(self, search_params: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for movies using TMDB API with structured parameters
        search_params should contain 'search_type' and 'params' keys
        """
        
        headers = {
            "Content-Type": "application/json"
        }
        
        search_type = search_params.get("search_type", "search")
        params = search_params.get("params", {})
        
        # Add API key and common parameters
        api_params = {
            "api_key": self.api_key,
            "include_adult": "false",
            "language": "en-US",
            "page": "1",
            **params
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Choose endpoint based on search type
            if search_type == "discover":
                movies = await self._discover_movies(client, headers, api_params, limit)
            else:  # search_type == "search"
                movies = await self._search_movies(client, headers, api_params, limit)
            
            return movies
    
    async def _discover_movies(self, client: httpx.AsyncClient, headers: Dict[str, str], 
                             params: Dict[str, str], limit: int) -> List[Dict[str, Any]]:
        """Use /discover/movie endpoint for filtered searches"""
        
        # Resolve person names to IDs if needed
        if "with_cast" in params:
            person_id = await self._get_person_id(client, headers, params["with_cast"])
            if person_id:
                params["with_cast"] = str(person_id)
            else:
                # Remove if person not found
                del params["with_cast"]
        
        if "with_crew" in params:
            person_id = await self._get_person_id(client, headers, params["with_crew"])
            if person_id:
                params["with_crew"] = str(person_id)
            else:
                del params["with_crew"]
        
        # Set default sorting if not specified
        if "sort_by" not in params:
            params["sort_by"] = "popularity.desc"
        
        response = await client.get(
            f"{self.base_url}/discover/movie",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        movies = data.get("results", [])
        
        return await self._format_movies(movies[:limit], client, headers)
    
    async def _search_movies(self, client: httpx.AsyncClient, headers: Dict[str, str], 
                           params: Dict[str, str], limit: int) -> List[Dict[str, Any]]:
        """Use /search/movie endpoint for title searches"""
        
        response = await client.get(
            f"{self.base_url}/search/movie",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        movies = data.get("results", [])
        
        return await self._format_movies(movies[:limit], client, headers)
    
    async def _get_person_id(self, client: httpx.AsyncClient, headers: Dict[str, str], 
                           person_name: str) -> Optional[int]:
        """Get person ID from name using /search/person"""
        try:
            response = await client.get(
                f"{self.base_url}/search/person",
                headers=headers,
                params={
                    "api_key": self.api_key,
                    "query": person_name,
                    "language": "en-US"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                # Return the first (most popular) match
                return results[0].get("id")
            
        except Exception as e:
            print(f"Error looking up person '{person_name}': {e}")
        
        return None
    
    async def _format_movies(self, movies: List[Dict[str, Any]], client: httpx.AsyncClient, 
                           headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Format movie data for frontend consumption"""
        
        # Get genre mapping for better display
        genre_map = await self._get_genre_mapping(client, headers)
        
        formatted_movies = []
        for movie in movies:
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