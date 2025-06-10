from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import requests
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# OMDB API Configuration
OMDB_API_KEY = os.environ['OMDB_API_KEY']
OMDB_BASE_URL = "http://www.omdbapi.com/"

# Models
class ContentItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    imdb_id: str
    title: str
    year: str
    content_type: str  # "movie" or "series"
    genre: str
    rating: Optional[str] = None
    poster: Optional[str] = None
    plot: Optional[str] = None
    director: Optional[str] = None
    actors: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Vote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_session: str
    winner_id: str
    loser_id: str
    content_type: str  # "movie" or "series"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vote_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class VotePair(BaseModel):
    item1: ContentItem
    item2: ContentItem
    content_type: str

class Recommendation(BaseModel):
    title: str
    reason: str
    poster: Optional[str] = None
    imdb_id: str

# OMDB API Functions
async def fetch_from_omdb(params: dict) -> dict:
    """Fetch data from OMDB API"""
    params["apikey"] = OMDB_API_KEY
    
    try:
        response = requests.get(OMDB_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("Response") == "False":
            raise HTTPException(status_code=404, detail=data.get("Error", "Not found"))
        
        return data
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"OMDB API error: {str(e)}")

async def search_and_store_content(title: str, content_type: str) -> Optional[ContentItem]:
    """Search OMDB and store content item"""
    params = {"t": title, "type": content_type}
    omdb_data = await fetch_from_omdb(params)
    
    content_item = ContentItem(
        imdb_id=omdb_data.get("imdbID"),
        title=omdb_data.get("Title"),
        year=omdb_data.get("Year"),
        content_type="movie" if omdb_data.get("Type") == "movie" else "series",
        genre=omdb_data.get("Genre", ""),
        rating=omdb_data.get("imdbRating"),
        poster=omdb_data.get("Poster") if omdb_data.get("Poster") != "N/A" else None,
        plot=omdb_data.get("Plot"),
        director=omdb_data.get("Director"),
        actors=omdb_data.get("Actors")
    )
    
    # Store in database
    await db.content.insert_one(content_item.dict())
    return content_item

# Initialize popular content
POPULAR_MOVIES = [
    "The Shawshank Redemption", "The Godfather", "The Dark Knight", "Pulp Fiction",
    "Forrest Gump", "Inception", "The Matrix", "Goodfellas", "The Silence of the Lambs",
    "Se7en", "Saving Private Ryan", "Interstellar", "The Departed", "The Prestige",
    "Fight Club", "The Lion King", "Gladiator", "Titanic", "Avatar", "Avengers: Endgame",
    "Spider-Man: No Way Home", "Top Gun: Maverick", "Jurassic Park", "Star Wars", "Casablanca"
]

POPULAR_TV_SHOWS = [
    "Breaking Bad", "Game of Thrones", "The Sopranos", "The Wire", "Friends",
    "The Office", "Stranger Things", "The Crown", "Sherlock", "True Detective",
    "House of Cards", "Narcos", "Black Mirror", "Westworld", "The Mandalorian",
    "Better Call Saul", "Ozark", "The Queen's Gambit", "Succession", "Euphoria",
    "The Bear", "Wednesday", "House of the Dragon", "The Last of Us", "Yellowstone"
]

# API Routes
@api_router.post("/initialize-content")
async def initialize_content():
    """Initialize database with popular movies and TV shows"""
    try:
        # Check if content already exists
        existing_count = await db.content.count_documents({})
        if existing_count > 0:
            return {"message": f"Content already initialized with {existing_count} items"}
        
        initialized = {"movies": 0, "series": 0, "errors": []}
        
        # Add movies
        for movie in POPULAR_MOVIES[:15]:  # Limit to avoid API rate limits
            try:
                await search_and_store_content(movie, "movie")
                initialized["movies"] += 1
            except Exception as e:
                initialized["errors"].append(f"Movie {movie}: {str(e)}")
        
        # Add TV shows
        for show in POPULAR_TV_SHOWS[:15]:  # Limit to avoid API rate limits
            try:
                await search_and_store_content(show, "series")
                initialized["series"] += 1
            except Exception as e:
                initialized["errors"].append(f"Series {show}: {str(e)}")
        
        return initialized
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/session")
async def create_session() -> UserSession:
    """Create a new user session"""
    session = UserSession()
    await db.sessions.insert_one(session.dict())
    return session

@api_router.get("/session/{session_id}")
async def get_session(session_id: str) -> UserSession:
    """Get session info"""
    session_data = await db.sessions.find_one({"session_id": session_id})
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    return UserSession(**session_data)

@api_router.get("/voting-pair/{session_id}")
async def get_voting_pair(session_id: str) -> VotePair:
    """Get a pair of items for voting (same content type only)"""
    # Verify session exists
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Randomly choose content type (movie or series)
    content_type = random.choice(["movie", "series"])
    
    # Get items of the same type
    items = await db.content.find({"content_type": content_type}).to_list(length=None)
    
    if len(items) < 2:
        raise HTTPException(status_code=400, detail=f"Not enough {content_type} content available")
    
    # Get user's vote history to avoid showing same pairs
    user_votes = await db.votes.find({"user_session": session_id}).to_list(length=None)
    voted_pairs = set()
    for vote in user_votes:
        pair = frozenset([vote["winner_id"], vote["loser_id"]])
        voted_pairs.add(pair)
    
    # Find an unvoted pair
    max_attempts = 50
    for _ in range(max_attempts):
        pair = random.sample(items, 2)
        item_ids = frozenset([pair[0]["id"], pair[1]["id"]])
        if item_ids not in voted_pairs:
            return VotePair(
                item1=ContentItem(**pair[0]),
                item2=ContentItem(**pair[1]),
                content_type=content_type
            )
    
    # If all pairs voted, return random pair
    pair = random.sample(items, 2)
    return VotePair(
        item1=ContentItem(**pair[0]),
        item2=ContentItem(**pair[1]),
        content_type=content_type
    )

@api_router.post("/vote")
async def submit_vote(vote_data: dict):
    """Submit a vote and update session"""
    required_fields = ["session_id", "winner_id", "loser_id", "content_type"]
    for field in required_fields:
        if field not in vote_data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    
    # Create vote record
    vote = Vote(
        user_session=vote_data["session_id"],
        winner_id=vote_data["winner_id"],
        loser_id=vote_data["loser_id"],
        content_type=vote_data["content_type"]
    )
    
    await db.votes.insert_one(vote.dict())
    
    # Update session vote count
    await db.sessions.update_one(
        {"session_id": vote_data["session_id"]},
        {"$inc": {"vote_count": 1}}
    )
    
    # Get updated session
    session = await db.sessions.find_one({"session_id": vote_data["session_id"]})
    
    return {
        "vote_recorded": True,
        "total_votes": session["vote_count"],
        "recommendations_available": session["vote_count"] >= 36
    }

@api_router.get("/recommendations/{session_id}")
async def get_recommendations(session_id: str) -> List[Recommendation]:
    """Get recommendations based on voting history"""
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["vote_count"] < 36:
        raise HTTPException(status_code=400, detail="Need at least 36 votes for recommendations")
    
    # Get user's votes
    user_votes = await db.votes.find({"user_session": session_id}).to_list(length=None)
    
    # Count wins for each item
    win_counts = {}
    for vote in user_votes:
        winner_id = vote["winner_id"]
        win_counts[winner_id] = win_counts.get(winner_id, 0) + 1
    
    # Get top winners
    sorted_winners = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)
    top_winner_ids = [item[0] for item in sorted_winners[:10]]
    
    # Get content details for top winners
    recommendations = []
    for winner_id in top_winner_ids[:5]:  # Top 5 recommendations
        content = await db.content.find_one({"id": winner_id})
        if content:
            win_count = win_counts[winner_id]
            total_appearances = sum(1 for vote in user_votes 
                                  if vote["winner_id"] == winner_id or vote["loser_id"] == winner_id)
            win_rate = (win_count / total_appearances) * 100 if total_appearances > 0 else 0
            
            recommendations.append(Recommendation(
                title=content["title"],
                reason=f"You chose this {win_count} times ({win_rate:.0f}% win rate)",
                poster=content.get("poster"),
                imdb_id=content["imdb_id"]
            ))
    
    return recommendations

@api_router.get("/stats/{session_id}")
async def get_user_stats(session_id: str):
    """Get user voting statistics"""
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_votes = await db.votes.find({"user_session": session_id}).to_list(length=None)
    
    # Count by content type
    movie_votes = len([v for v in user_votes if v["content_type"] == "movie"])
    series_votes = len([v for v in user_votes if v["content_type"] == "series"])
    
    return {
        "total_votes": len(user_votes),
        "movie_votes": movie_votes,
        "series_votes": series_votes,
        "votes_until_recommendations": max(0, 36 - len(user_votes)),
        "recommendations_available": len(user_votes) >= 36
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
