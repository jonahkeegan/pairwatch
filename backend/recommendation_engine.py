"""
Advanced ML-Powered Recommendation Engine for Movie/TV Preferences

This module implements sophisticated content discovery using:
1. Collaborative Filtering
2. Content-Based Filtering 
3. Hybrid Recommendation System
4. User Preference Learning
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csr_matrix
import json
from datetime import datetime, timedelta

class AdvancedRecommendationEngine:
    def __init__(self):
        self.content_features = None
        self.user_profiles = {}
        self.content_similarity_matrix = None
        self.genre_vectorizer = TfidfVectorizer()
        self.cast_vectorizer = TfidfVectorizer()
        self.svd_model = TruncatedSVD(n_components=50, random_state=42)
        
    def extract_content_features(self, content_items: List[Dict]) -> pd.DataFrame:
        """Extract and engineer features from content metadata"""
        features = []
        
        for item in content_items:
            # Basic features
            feature_dict = {
                'content_id': item['id'],
                'title': item['title'],
                'content_type': item['content_type'],
                'year': self._extract_year(item['year']),
                'rating': self._safe_float(item.get('rating', 0)),
                'genre_primary': self._extract_primary_genre(item.get('genre', '')),
                'decade': self._get_decade(item['year']),
            }
            
            # Advanced features
            feature_dict.update(self._extract_genre_features(item.get('genre', '')))
            feature_dict.update(self._extract_cast_features(item.get('actors', ''), item.get('director', '')))
            feature_dict.update(self._extract_content_quality_features(item))
            
            features.append(feature_dict)
        
        return pd.DataFrame(features)
    
    def _extract_year(self, year_str: str) -> int:
        """Extract numeric year from year string"""
        try:
            return int(year_str.split('–')[0]) if year_str else 2000
        except:
            return 2000
    
    def _safe_float(self, value) -> float:
        """Safely convert to float"""
        try:
            return float(value) if value and value != 'N/A' else 0.0
        except:
            return 0.0
    
    def _extract_primary_genre(self, genre_str: str) -> str:
        """Extract primary genre"""
        genres = genre_str.split(',') if genre_str else ['Unknown']
        return genres[0].strip()
    
    def _get_decade(self, year_str: str) -> str:
        """Get decade from year"""
        year = self._extract_year(year_str)
        decade = (year // 10) * 10
        return f"{decade}s"
    
    def _extract_genre_features(self, genre_str: str) -> Dict:
        """Extract genre-based features"""
        genres = [g.strip().lower() for g in genre_str.split(',')] if genre_str else []
        
        # Genre categories
        action_genres = ['action', 'adventure', 'thriller']
        drama_genres = ['drama', 'romance', 'biography']
        comedy_genres = ['comedy', 'family', 'animation']
        serious_genres = ['documentary', 'history', 'war']
        fantasy_genres = ['fantasy', 'sci-fi', 'horror', 'mystery']
        
        return {
            'is_action': any(g in action_genres for g in genres),
            'is_drama': any(g in drama_genres for g in genres),
            'is_comedy': any(g in comedy_genres for g in genres),
            'is_serious': any(g in serious_genres for g in genres),
            'is_fantasy': any(g in fantasy_genres for g in genres),
            'genre_diversity': len(genres),
            'genres_text': genre_str.lower()
        }
    
    def _extract_cast_features(self, actors_str: str, director_str: str) -> Dict:
        """Extract cast and crew features"""
        return {
            'director': director_str if director_str and director_str != 'N/A' else '',
            'actors': actors_str if actors_str and actors_str != 'N/A' else '',
            'has_known_director': bool(director_str and director_str != 'N/A'),
            'cast_size': len(actors_str.split(',')) if actors_str and actors_str != 'N/A' else 0
        }
    
    def _extract_content_quality_features(self, item: Dict) -> Dict:
        """Extract content quality indicators"""
        rating = self._safe_float(item.get('rating', 0))
        
        return {
            'high_rated': rating >= 8.0,
            'well_rated': rating >= 7.0,
            'has_poster': bool(item.get('poster')),
            'has_plot': bool(item.get('plot')),
            'content_completeness': sum([
                bool(item.get('poster')),
                bool(item.get('plot')),
                bool(item.get('director')),
                bool(item.get('actors')),
                rating > 0
            ])
        }
    
    def build_user_profile(self, user_interactions: List[Dict]) -> Dict:
        """Build comprehensive user preference profile"""
        profile = {
            'genre_preferences': {},
            'decade_preferences': {},
            'quality_preference': 0.0,
            'content_type_preference': {'movie': 0.5, 'series': 0.5},
            'director_preferences': {},
            'actor_preferences': {},
            'interaction_patterns': {},
            'preference_strength': 0.0
        }
        
        if not user_interactions:
            return profile
        
        # Analyze interactions
        positive_interactions = [i for i in user_interactions 
                               if i['interaction_type'] in ['vote_winner', 'want_to_watch', 'watched']]
        negative_interactions = [i for i in user_interactions 
                               if i['interaction_type'] in ['vote_loser', 'not_interested']]
        
        # Build preference weights
        total_positive = len(positive_interactions)
        total_negative = len(negative_interactions)
        
        if total_positive > 0:
            profile['preference_strength'] = total_positive / max(1, total_positive + total_negative)
        
        # Extract preferences from positive interactions
        for interaction in positive_interactions:
            content = interaction.get('content', {})
            weight = self._get_interaction_weight(interaction['interaction_type'])
            
            # Genre preferences
            genres = content.get('genre', '').split(',')
            for genre in genres:
                genre = genre.strip()
                if genre:
                    profile['genre_preferences'][genre] = profile['genre_preferences'].get(genre, 0) + weight
            
            # Decade preferences
            decade = self._get_decade(content.get('year', ''))
            profile['decade_preferences'][decade] = profile['decade_preferences'].get(decade, 0) + weight
            
            # Content type preferences
            content_type = content.get('content_type', 'movie')
            profile['content_type_preference'][content_type] += weight * 0.1
            
            # Quality preference
            rating = self._safe_float(content.get('rating', 0))
            if rating > 0:
                profile['quality_preference'] += rating * weight
        
        # Normalize preferences
        profile = self._normalize_preferences(profile)
        return profile
    
    def _get_interaction_weight(self, interaction_type: str) -> float:
        """Get weight for different interaction types"""
        weights = {
            'want_to_watch': 1.0,
            'watched': 0.8,
            'vote_winner': 0.6,
            'vote_loser': -0.3,
            'not_interested': -0.5
        }
        return weights.get(interaction_type, 0.0)
    
    def _normalize_preferences(self, profile: Dict) -> Dict:
        """Normalize preference weights"""
        # Normalize genre preferences
        if profile['genre_preferences']:
            total_genre_weight = sum(profile['genre_preferences'].values())
            if total_genre_weight > 0:
                for genre in profile['genre_preferences']:
                    profile['genre_preferences'][genre] /= total_genre_weight
        
        # Normalize decade preferences
        if profile['decade_preferences']:
            total_decade_weight = sum(profile['decade_preferences'].values())
            if total_decade_weight > 0:
                for decade in profile['decade_preferences']:
                    profile['decade_preferences'][decade] /= total_decade_weight
        
        # Normalize content type preferences
        total_content_weight = sum(profile['content_type_preference'].values())
        if total_content_weight > 0:
            for content_type in profile['content_type_preference']:
                profile['content_type_preference'][content_type] /= total_content_weight
        
        return profile
    
    def calculate_content_similarity(self, content_df: pd.DataFrame):
        """Calculate content-to-content similarity matrix"""
        # Create feature vectors for content-based filtering
        features = []
        
        for _, item in content_df.iterrows():
            feature_vector = []
            
            # Numerical features
            feature_vector.extend([
                item['year'] / 2025.0,  # Normalize year
                item['rating'] / 10.0,  # Normalize rating
                item['content_completeness'] / 5.0,  # Normalize completeness
                float(item['is_action']),
                float(item['is_drama']),
                float(item['is_comedy']),
                float(item['is_serious']),
                float(item['is_fantasy']),
                item['genre_diversity'] / 5.0,  # Normalize diversity
            ])
            
            features.append(feature_vector)
        
        # Calculate similarity matrix
        features_array = np.array(features)
        self.content_similarity_matrix = cosine_similarity(features_array)
        
        return self.content_similarity_matrix
    
    def generate_recommendations(self, user_profile: Dict, content_df: pd.DataFrame, 
                               watched_content_ids: List[str], num_recommendations: int = 10) -> List[Dict]:
        """Generate personalized recommendations using hybrid approach"""
        
        if content_df.empty:
            return []
        
        # Filter out watched content
        unwatched_content = content_df[~content_df['content_id'].isin(watched_content_ids)]
        
        if unwatched_content.empty:
            return []
        
        # Calculate recommendation scores
        recommendations = []
        
        for _, content in unwatched_content.iterrows():
            score = self._calculate_recommendation_score(content, user_profile)
            
            recommendations.append({
                'content_id': content['content_id'],
                'title': content['title'],
                'score': score,
                'reasoning': self._generate_reasoning(content, user_profile),
                'content_type': content['content_type'],
                'rating': content['rating'],
                'year': content['year'],
                'genre': content.get('genres_text', ''),
                'poster': content.get('poster', ''),
                'confidence': min(user_profile.get('preference_strength', 0.5) * 2, 1.0)
            })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:num_recommendations]
    
    def _calculate_recommendation_score(self, content: pd.Series, user_profile: Dict) -> float:
        """Calculate recommendation score for a content item"""
        score = 0.0
        
        # Genre preference score (40% weight)
        genre_score = self._calculate_genre_score(content, user_profile)
        score += genre_score * 0.4
        
        # Quality score (25% weight)
        quality_score = content['rating'] / 10.0 if content['rating'] > 0 else 0.5
        score += quality_score * 0.25
        
        # Content type preference (20% weight)
        content_type_score = user_profile['content_type_preference'].get(content['content_type'], 0.5)
        score += content_type_score * 0.2
        
        # Decade preference (10% weight)
        decade_score = user_profile['decade_preferences'].get(content['decade'], 0.1)
        score += decade_score * 0.1
        
        # Recency bonus (5% weight)
        current_year = datetime.now().year
        recency_score = max(0, 1 - (current_year - content['year']) / 50)
        score += recency_score * 0.05
        
        return min(score, 1.0)
    
    def _calculate_genre_score(self, content: pd.Series, user_profile: Dict) -> float:
        """Calculate genre preference score"""
        content_genres = content.get('genres_text', '').split(',')
        content_genres = [g.strip() for g in content_genres if g.strip()]
        
        if not content_genres or not user_profile['genre_preferences']:
            return 0.5  # Neutral score
        
        total_score = 0.0
        matched_genres = 0
        
        for genre in content_genres:
            if genre in user_profile['genre_preferences']:
                total_score += user_profile['genre_preferences'][genre]
                matched_genres += 1
        
        return total_score / max(1, matched_genres) if matched_genres > 0 else 0.2
    
    def _generate_reasoning(self, content: pd.Series, user_profile: Dict) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        # Genre-based reasoning
        content_genres = content.get('genres_text', '').split(',')
        content_genres = [g.strip() for g in content_genres if g.strip()]
        
        top_user_genres = sorted(user_profile['genre_preferences'].items(), 
                               key=lambda x: x[1], reverse=True)[:3]
        
        for genre in content_genres:
            if genre in [g[0] for g in top_user_genres]:
                reasons.append(f"matches your preference for {genre}")
                break
        
        # Quality-based reasoning
        if content['rating'] >= 8.0:
            reasons.append("highly rated content")
        elif content['rating'] >= 7.0:
            reasons.append("well-reviewed")
        
        # Recency reasoning
        current_year = datetime.now().year
        if current_year - content['year'] <= 3:
            reasons.append("recent release")
        
        # Content type reasoning
        content_type_pref = user_profile['content_type_preference'].get(content['content_type'], 0.5)
        if content_type_pref > 0.6:
            reasons.append(f"matches your {content['content_type']} preference")
        
        if not reasons:
            reasons.append("explores new content areas")
        
        return "Recommended because it " + " and ".join(reasons[:3])

# Additional metadata suggestions for enhanced predictions
ENHANCED_METADATA_SOURCES = {
    "tmdb_api": {
        "description": "The Movie Database - more comprehensive than OMDB",
        "features": [
            "Detailed cast and crew information",
            "User ratings and reviews", 
            "Production companies and budgets",
            "Streaming platform availability",
            "Similar movie suggestions",
            "Popularity and vote counts",
            "Keyword tags and themes"
        ]
    },
    "streaming_availability": {
        "description": "JustWatch or Streaming Availability API",
        "features": [
            "Current streaming platform availability",
            "Rental/purchase pricing",
            "Regional availability",
            "Recently added/leaving platforms"
        ]
    },
    "user_demographics": {
        "description": "Optional user profile data",
        "features": [
            "Age range for age-appropriate recommendations",
            "Location for regional content preferences",
            "Language preferences",
            "Time zone for viewing time analysis"
        ]
    },
    "behavioral_data": {
        "description": "User interaction patterns",
        "features": [
            "Time of day preferences",
            "Binge watching patterns",
            "Completion rates",
            "Re-watch behavior",
            "Social sharing activity"
        ]
    },
    "social_features": {
        "description": "Social recommendation signals",
        "features": [
            "Friends' preferences and ratings",
            "Social media mentions and trends",
            "Community ratings and reviews",
            "Watch party activity"
        ]
    },
    "content_analysis": {
        "description": "Deep content understanding",
        "features": [
            "Sentiment analysis of reviews",
            "Thematic analysis of plots",
            "Visual style analysis",
            "Mood and tone classification",
            "Complexity and sophistication scores"
        ]
    }
}