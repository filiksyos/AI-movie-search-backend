import httpx
import json
from typing import Dict, Any, Optional
import re

class QueryTranslator:
    def __init__(self, openrouter_api_key: str):
        self.api_key = openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Genre mapping: name -> TMDB ID
        self.genre_map = {
            "action": 28,
            "adventure": 12,
            "animation": 16,
            "comedy": 35,
            "crime": 80,
            "documentary": 99,
            "drama": 18,
            "family": 10751,
            "fantasy": 14,
            "history": 36,
            "horror": 27,
            "music": 10402,
            "mystery": 9648,
            "romance": 10749,
            "science fiction": 878,
            "sci-fi": 878,
            "thriller": 53,
            "war": 10752,
            "western": 37
        }
        
    async def translate_query(self, natural_query: str) -> Dict[str, Any]:
        """
        Translate natural language query to TMDB discover/search parameters
        Returns dict with 'search_type' and 'params' keys
        """
        
        # Check if API key is available
        if not self.api_key or self.api_key == "":
            print("OpenRouter API key not set, using fallback rule-based translation")
            return self._translate_with_rules(natural_query)
        
        # Try OpenRouter API first
        try:
            return await self._translate_with_ai(natural_query)
        except Exception as e:
            print(f"OpenRouter API failed, using fallback: {e}")
            # Fallback to rule-based translation
            return self._translate_with_rules(natural_query)
    
    async def _translate_with_ai(self, natural_query: str) -> Dict[str, Any]:
        """Use OpenRouter AI for translation"""
        system_prompt = """You are an expert at converting natural language movie search queries into TMDB (The Movie Database) API parameters.

Your task is to analyze the user's natural language query and return search parameters in XML format.

Use this XML structure:
<search>
    <type>discover</type> <!-- or "search" -->
    <params>
        <param name="parameter_name">value</param>
        <!-- additional params as needed -->
    </params>
</search>

For "discover" type (use for genre, year, rating, actor filters):
- with_genres: genre IDs (action=28, comedy=35, drama=18, horror=27, sci-fi=878, thriller=53, romance=10749, animation=16, crime=80, fantasy=14)
- primary_release_year: YYYY format
- vote_average.gte: minimum rating (1-10)
- with_cast: person name for actor search
- with_crew: person name for director search
- sort_by: popularity.desc, vote_average.desc, release_date.desc

For "search" type (use for specific movie titles):
- query: exact movie title or partial title

Examples:

Input: "action movies from 2020"
Output:
<search>
    <type>discover</type>
    <params>
        <param name="with_genres">28</param>
        <param name="primary_release_year">2020</param>
    </params>
</search>

Input: "comedies with high ratings"
Output:
<search>
    <type>discover</type>
    <params>
        <param name="with_genres">35</param>
        <param name="vote_average.gte">7.5</param>
    </params>
</search>

Input: "movies starring Tom Hanks"
Output:
<search>
    <type>discover</type>
    <params>
        <param name="with_cast">Tom Hanks</param>
    </params>
</search>

Input: "The Dark Knight"
Output:
<search>
    <type>search</type>
    <params>
        <param name="query">The Dark Knight</param>
    </params>
</search>

Return ONLY the XML, no other text or formatting."""

        user_prompt = f"Convert this movie search query: {natural_query}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "AI Movie Search"
        }
        
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=data)
                response.raise_for_status()
                
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"].strip()
                
                # Parse XML response
                try:
                    parsed_result = self._parse_xml_response(ai_response)
                    return self._validate_and_process_params(parsed_result)
                except Exception as e:
                    print(f"AI returned unparseable response: {ai_response}")
                    print(f"Parse error: {e}")
                    return self._translate_with_rules(natural_query)
                    
            except httpx.HTTPStatusError as e:
                print(f"OpenRouter API HTTP error: {e.response.status_code} - {e.response.text}")
                return self._translate_with_rules(natural_query)
            except Exception as e:
                print(f"OpenRouter API error: {str(e)}")
                return self._translate_with_rules(natural_query)
    
    def _parse_xml_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse XML response into structured parameters"""
        # Extract search type
        type_match = re.search(r'<type>(.*?)</type>', xml_response, re.DOTALL)
        search_type = type_match.group(1).strip() if type_match else "search"
        
        # Extract parameters
        params = {}
        param_matches = re.findall(r'<param name="([^"]+)">(.*?)</param>', xml_response, re.DOTALL)
        
        for param_name, param_value in param_matches:
            params[param_name.strip()] = param_value.strip()
        
        return {
            "search_type": search_type,
            "params": params
        }
    
    def _validate_and_process_params(self, parsed_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and process AI-generated parameters"""
        search_type = parsed_result.get("search_type", "search")
        params = parsed_result.get("params", {})
        
        # Process genre names to IDs if needed
        if "with_genres" in params:
            genre_value = params["with_genres"]
            if isinstance(genre_value, str) and not genre_value.isdigit():
                # Convert genre name to ID
                genre_name = genre_value.lower()
                if genre_name in self.genre_map:
                    params["with_genres"] = str(self.genre_map[genre_name])
        
        return {
            "search_type": search_type,
            "params": params
        }
    
    def _translate_with_rules(self, natural_query: str) -> Dict[str, Any]:
        """Fallback rule-based translation"""
        query = natural_query.lower()
        params = {}
        search_type = "discover"
        
        # Check for specific movie title patterns
        if any(phrase in query for phrase in ["find movie", "movie called", "film called"]):
            # Extract movie title
            for phrase in ["find movie", "movie called", "film called"]:
                if phrase in query:
                    title = query.split(phrase)[-1].strip()
                    return {
                        "search_type": "search",
                        "params": {"query": title}
                    }
        
        # Genre detection (improved to catch more variations)
        for genre_name, genre_id in self.genre_map.items():
            if genre_name in query or f"{genre_name} movie" in query or f"{genre_name} film" in query:
                params["with_genres"] = str(genre_id)
                break
        
        # Year detection
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        if year_match:
            params["primary_release_year"] = year_match.group()
        
        # Rating detection
        if any(phrase in query for phrase in ["high rating", "good rating", "top rated", "best"]):
            params["vote_average.gte"] = "7.5"
        
        # Actor detection
        if "starring" in query or "with " in query:
            # Simple actor name extraction (can be improved)
            if "starring" in query:
                actor_part = query.split("starring")[-1].strip()
                actor_name = actor_part.split(" in ")[0].split(" from ")[0].strip()
                if len(actor_name.split()) <= 3:  # Reasonable name length
                    params["with_cast"] = actor_name.title()
        
        # If no specific parameters found, try keyword search
        if not params:
            # Extract meaningful keywords and try title search
            words = query.split()
            stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "movies", "films", "movie", "film", "search", "find", "show", "me"}
            keywords = [word for word in words if word not in stop_words and len(word) > 2]
            
            if keywords:
                # Use search endpoint with extracted keywords
                search_query = " ".join(keywords[:3])  # Use first 3 meaningful words
                return {
                    "search_type": "search",
                    "params": {"query": search_query}
                }
            else:
                # Last resort: show popular movies
                return {
                    "search_type": "discover",
                    "params": {
                        "sort_by": "popularity.desc",
                        "vote_count.gte": "200"
                    }
                }
        
        return {
            "search_type": search_type,
            "params": params
        } 