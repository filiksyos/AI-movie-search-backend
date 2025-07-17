import httpx
import json
from typing import Dict, Any, Optional

class QueryTranslator:
    def __init__(self, openrouter_api_key: str):
        self.api_key = openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    async def translate_query(self, natural_query: str) -> str:
        """
        Translate natural language query to TMDB search parameters
        """
        
        # Try OpenRouter API first
        try:
            return await self._translate_with_ai(natural_query)
        except Exception as e:
            print(f"OpenRouter API failed, using fallback: {e}")
            # Fallback to rule-based translation
            return self._translate_with_rules(natural_query)
    
    async def _translate_with_ai(self, natural_query: str) -> str:
        """Use OpenRouter AI for translation"""
        system_prompt = """You are an expert at converting natural language movie search queries into TMDB (The Movie Database) API search parameters.

Your task is to analyze the user's natural language query and return a simple search string that can be used with TMDB's search API.

Guidelines:
1. Extract key movie attributes: genre, year/decade, rating, actors, directors, keywords
2. Focus on the most important search terms that will yield relevant results
3. Keep it simple - TMDB search works best with straightforward queries
4. If the query mentions specific movies, actors, or directors, prioritize those
5. For genre/year combinations, include both in the search string
6. For rating requirements, focus on the search terms and let filtering handle ratings

Examples:
- "Action movies from the 90s" → "action 1990s"
- "Sci-fi films with time travel" → "science fiction time travel"
- "Movies starring Leonardo DiCaprio" → "Leonardo DiCaprio"
- "Horror films from 2020" → "horror 2020"
- "Romantic comedies with high ratings" → "romantic comedy"
- "Marvel superhero movies" → "Marvel superhero"

Return ONLY the search string, nothing else."""

        user_prompt = f"Convert this movie search query to TMDB search terms: {natural_query}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "AI Movie Search"
        }
        
        data = {
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 100
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            translated_query = result["choices"][0]["message"]["content"].strip()
            
            # Clean up the response - remove quotes and extra formatting
            translated_query = translated_query.strip('"\'`')
            
            return translated_query
    
    def _translate_with_rules(self, natural_query: str) -> str:
        """Fallback rule-based translation"""
        query = natural_query.lower()
        
        # Common movie search patterns
        patterns = {
            # Actors/Directors
            r'(movies?\s+starring|starring|with)\s+([a-zA-Z\s]+)': r'\2',
            r'(directed by|by director)\s+([a-zA-Z\s]+)': r'\2',
            
            # Years/Decades
            r'from\s+the\s+(\d{2})s': r'\1',
            r'in\s+(\d{4})': r'\1',
            r'(\d{4})\s+(movies?|films?)': r'\1',
            
            # Genres
            r'action\s+(movies?|films?)': 'action',
            r'horror\s+(movies?|films?)': 'horror',
            r'comedy\s+(movies?|films?)': 'comedy',
            r'romantic?\s+comed(y|ies)': 'romantic comedy',
            r'sci-?fi': 'science fiction',
            r'science\s+fiction': 'science fiction',
            r'superhero': 'superhero',
            r'marvel': 'marvel',
            r'dc\s+comics?': 'dc',
            
            # Keywords
            r'time\s+travel': 'time travel',
            r'space': 'space',
            r'alien': 'alien',
            r'zombie': 'zombie',
            r'vampire': 'vampire',
            
            # Ratings (remove these, focus on content)
            r'(high|good|top)\s+rat(ed|ing)': '',
            r'popular': '',
            r'best': '',
        }
        
        import re
        result_terms = []
        
        # Apply patterns
        for pattern, replacement in patterns.items():
            match = re.search(pattern, query)
            if match:
                if replacement.startswith('\\'):
                    # Backreference
                    term = re.sub(pattern, replacement, query).strip()
                    if term:
                        result_terms.append(term)
                else:
                    result_terms.append(replacement)
        
        # If no patterns matched, extract key words
        if not result_terms:
            # Remove common words and extract meaningful terms
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'movies', 'films', 'movie', 'film'}
            words = [word for word in query.split() if word not in stop_words and len(word) > 2]
            result_terms = words[:3]  # Take first 3 meaningful words
        
        # Clean and join terms
        final_query = ' '.join(result_terms).strip()
        return final_query if final_query else natural_query 