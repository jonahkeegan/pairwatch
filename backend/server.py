from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime, timedelta
import requests
import random
import jwt
import asyncio
from recommendation_engine import AdvancedRecommendationEngine
from passlib.context import CryptContext
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
JWT_ALGORITHM = os.environ['JWT_ALGORITHM']
JWT_EXPIRATION_HOURS = int(os.environ['JWT_EXPIRATION_HOURS'])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# OMDB API Configuration
OMDB_API_KEY = os.environ['OMDB_API_KEY']
OMDB_BASE_URL = "http://www.omdbapi.com/"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    password_hash: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    total_votes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    total_votes: int
    created_at: datetime
    last_login: Optional[datetime] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserProfile

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
    user_id: Optional[str] = None  # For registered users
    session_id: Optional[str] = None  # For guest users
    winner_id: str
    loser_id: str
    content_type: str  # "movie" or "series"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserContentInteraction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    content_id: str
    interaction_type: str  # "vote_winner", "vote_loser", "watched", "want_to_watch", "not_interested"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserWatchlist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_id: str
    added_at: datetime = Field(default_factory=datetime.utcnow)
    priority: int = 1  # 1-5 scale for urgency (user-defined)
    watchlist_type: str = "user_defined"  # "user_defined" or "algo_predicted"

class AlgoRecommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_id: str
    recommendation_score: float
    reasoning: str
    confidence: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    viewed: bool = False
    user_action: Optional[str] = None  # "added_to_watchlist", "dismissed", "not_interested"

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

# Authentication Functions
def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """Get current user from JWT token"""
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None
    
    user_data = await db.users.find_one({"id": user_id})
    if user_data is None:
        return None
    
    return User(**user_data)

# OMDB API Functions (keeping existing ones)
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

# Initialize popular content - Expanded for richer experience
POPULAR_MOVIES = [
    # Classic Films
    "The Shawshank Redemption", "The Godfather", "The Dark Knight", "Pulp Fiction",
    "Forrest Gump", "Inception", "The Matrix", "Goodfellas", "The Silence of the Lambs",
    "Se7en", "Saving Private Ryan", "Interstellar", "The Departed", "The Prestige",
    "Fight Club", "The Lion King", "Gladiator", "Titanic", "Avatar", "Casablanca",
    
    # Modern Blockbusters
    "Avengers: Endgame", "Spider-Man: No Way Home", "Top Gun: Maverick", "Jurassic Park",
    "Star Wars", "The Lord of the Rings: The Fellowship of the Ring", "The Empire Strikes Back",
    "Raiders of the Lost Ark", "Jaws", "E.T. the Extra-Terrestrial", "Back to the Future",
    "Terminator 2: Judgment Day", "Aliens", "Die Hard", "Heat", "Goodfellas",
    
    # Award Winners
    "Parasite", "Green Book", "Moonlight", "Birdman", "12 Years a Slave", "Argo",
    "The Artist", "The King's Speech", "Slumdog Millionaire", "No Country for Old Men",
    "The Departed", "Crash", "Million Dollar Baby", "Chicago", "A Beautiful Mind",
    
    # Action & Adventure
    "Mad Max: Fury Road", "John Wick", "Mission: Impossible - Fallout", "Casino Royale",
    "Iron Man", "Wonder Woman", "Black Panther", "Guardians of the Galaxy", "Thor: Ragnarok",
    "Captain America: The Winter Soldier", "Doctor Strange", "Ant-Man", "Deadpool",
    
    # Sci-Fi & Fantasy
    "Blade Runner 2049", "Arrival", "Ex Machina", "Her", "Gravity", "The Martian",
    "Dune", "Pacific Rim", "Edge of Tomorrow", "Minority Report", "The Fifth Element",
    "Star Trek", "Star Trek Into Darkness", "District 9", "Elysium", "Oblivion",
    
    # Horror & Thriller
    "Get Out", "A Quiet Place", "Hereditary", "The Conjuring", "It", "Halloween",
    "Scream", "The Sixth Sense", "The Others", "Shutter Island", "Gone Girl",
    "Zodiac", "Prisoners", "Sicario", "Hell or High Water", "Wind River",
    
    # Comedy
    "The Grand Budapest Hotel", "Superbad", "Anchorman", "Step Brothers", "Tropic Thunder",
    "Zoolander", "Meet the Parents", "Wedding Crashers", "The Hangover", "Bridesmaids",
    "Knives Out", "Game Night", "Tag", "Blockers", "Booksmart",
    
    # Drama
    "Manchester by the Sea", "Room", "Spotlight", "The Revenant", "Birdman", "Whiplash",
    "La La Land", "Call Me by Your Name", "Lady Bird", "Three Billboards Outside Ebbing, Missouri",
    "The Shape of Water", "First Man", "Vice", "Green Book", "Bohemian Rhapsody",
    
    # Animation
    "Toy Story", "Finding Nemo", "The Incredibles", "Up", "WALL-E", "Inside Out",
    "Coco", "Moana", "Frozen", "Zootopia", "Big Hero 6", "Wreck-It Ralph",
    "How to Train Your Dragon", "Shrek", "Monsters, Inc.", "Ratatouille",
    
    # International Cinema
    "Spirited Away", "Princess Mononoke", "Your Name", "Oldboy", "The Handmaiden",
    "Train to Busan", "Burning", "Roma", "Amour", "The Hunt", "Another Round",
    "Minari", "The Farewell", "Crazy Rich Asians", "Everything Everywhere All at Once"
]

POPULAR_TV_SHOWS = [
    # Drama Series
    "Breaking Bad", "Better Call Saul", "The Sopranos", "The Wire", "Mad Men",
    "True Detective", "Westworld", "House of Cards", "Succession", "Ozark",
    "Narcos", "Mindhunter", "Fargo", "The Crown", "Downton Abbey",
    
    # Fantasy & Sci-Fi
    "Game of Thrones", "House of the Dragon", "The Mandalorian", "Stranger Things",
    "Black Mirror", "The Boys", "The Umbrella Academy", "Loki", "WandaVision",
    "The Falcon and the Winter Soldier", "Star Trek: Discovery", "The Expanse",
    "Altered Carbon", "Lost", "Fringe", "The X-Files",
    
    # Comedy
    "The Office", "Friends", "Parks and Recreation", "Brooklyn Nine-Nine", "Arrested Development",
    "Community", "30 Rock", "Scrubs", "How I Met Your Mother", "The Big Bang Theory",
    "Modern Family", "Schitt's Creek", "Ted Lasso", "The Good Place", "Veep",
    
    # Thriller & Crime
    "Sherlock", "Dexter", "Prison Break", "24", "Homeland", "The Blacklist",
    "Money Heist", "Dark", "Bodyguard", "Line of Duty", "Mare of Easttown",
    "The Night Of", "The Sinner", "Broadchurch", "Top of the Lake", "Happy Valley",
    
    # Recent Hits
    "Wednesday", "The Bear", "Abbott Elementary", "House of the Dragon", "The Last of Us",
    "Only Murders in the Building", "Euphoria", "Yellowstone", "1883", "Mayor of Kingstown",
    "Hawkeye", "Ms. Marvel", "She-Hulk", "Moon Knight", "Obi-Wan Kenobi",
    
    # Classic TV
    "The Twilight Zone", "Cheers", "Seinfeld", "Frasier", "The West Wing",
    "ER", "Law & Order", "CSI", "NCIS", "Criminal Minds", "Bones",
    "House", "Grey's Anatomy", "Scandal", "How to Get Away with Murder",
    
    # Limited Series
    "The Queen's Gambit", "Chernobyl", "Band of Brothers", "The Pacific", "John Adams",
    "Angels in America", "The People v. O.J. Simpson", "The Assassination of Gianni Versace",
    "When They See Us", "Unbelievable", "Sharp Objects", "Big Little Lies",
    
    # International Shows
    "Squid Game", "Money Heist", "Dark", "Lupin", "Elite", "Cable Girls",
    "The Rain", "Ragnarok", "Young Royals", "Sex Education", "The Crown",
    "Peaky Blinders", "Sherlock", "Doctor Who", "Downton Abbey", "Call the Midwife",
    
    # Animated Series
    "Rick and Morty", "BoJack Horseman", "South Park", "The Simpsons", "Family Guy",
    "Bob's Burgers", "Archer", "Big Mouth", "F is for Family", "Disenchantment",
    
    # Documentary Series
    "Making a Murderer", "Tiger King", "Wild Wild Country", "The Staircase", "Serial",
    "True Crime", "The Jinx", "Going Clear", "Won't You Be My Neighbor", "Free Solo"
]

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password)
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token = create_access_token({"sub": user.id})
    
    # Update last login
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600,
        user=UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            total_votes=user.total_votes,
            created_at=user.created_at,
            last_login=datetime.utcnow()
        )
    )

@api_router.post("/auth/login", response_model=Token)
async def login_user(login_data: UserLogin):
    """Login user"""
    user_data = await db.users.find_one({"email": login_data.email})
    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    user = User(**user_data)
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token({"sub": user.id})
    
    # Update last login
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600,
        user=UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            total_votes=user.total_votes,
            created_at=user.created_at,
            last_login=datetime.utcnow()
        )
    )

@api_router.get("/auth/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        total_votes=current_user.total_votes,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@api_router.put("/auth/profile", response_model=UserProfile)
async def update_user_profile(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user profile"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.bio is not None:
        update_data["bio"] = profile_data.bio
    if profile_data.avatar_url is not None:
        update_data["avatar_url"] = profile_data.avatar_url
    
    if update_data:
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": update_data}
        )
        
        # Get updated user
        updated_user_data = await db.users.find_one({"id": current_user.id})
        updated_user = User(**updated_user_data)
        
        return UserProfile(
            id=updated_user.id,
            email=updated_user.email,
            name=updated_user.name,
            avatar_url=updated_user.avatar_url,
            bio=updated_user.bio,
            total_votes=updated_user.total_votes,
            created_at=updated_user.created_at,
            last_login=updated_user.last_login
        )
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        total_votes=current_user.total_votes,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

# Content and Voting Routes (Updated to support both users and sessions)
@api_router.post("/initialize-content")
async def initialize_content():
    """Initialize database with popular movies and TV shows"""
    try:
        # Check if content already exists
        existing_count = await db.content.count_documents({})
        if existing_count > 100:  # Only reinitialize if we have less than 100 items
            return {"message": f"Content already initialized with {existing_count} items"}
        
        initialized = {"movies": 0, "series": 0, "errors": [], "skipped": 0}
        
        # Process movies in batches to respect API limits
        print(f"Initializing {len(POPULAR_MOVIES)} movies...")
        for i, movie in enumerate(POPULAR_MOVIES):
            try:
                # Check if movie already exists
                existing_movie = await db.content.find_one({"title": movie, "content_type": "movie"})
                if existing_movie:
                    initialized["skipped"] += 1
                    continue
                    
                await search_and_store_content(movie, "movie")
                initialized["movies"] += 1
                print(f"Added movie {i+1}/{len(POPULAR_MOVIES)}: {movie}")
                
                # Small delay to be respectful to OMDB API
                if i % 10 == 0 and i > 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                error_msg = f"Movie {movie}: {str(e)}"
                initialized["errors"].append(error_msg)
                print(f"Error adding {movie}: {str(e)}")
        
        # Process TV shows in batches
        print(f"Initializing {len(POPULAR_TV_SHOWS)} TV shows...")
        for i, show in enumerate(POPULAR_TV_SHOWS):
            try:
                # Check if show already exists
                existing_show = await db.content.find_one({"title": show, "content_type": "series"})
                if existing_show:
                    initialized["skipped"] += 1
                    continue
                    
                await search_and_store_content(show, "series")
                initialized["series"] += 1
                print(f"Added TV show {i+1}/{len(POPULAR_TV_SHOWS)}: {show}")
                
                # Small delay to be respectful to OMDB API
                if i % 10 == 0 and i > 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                error_msg = f"Series {show}: {str(e)}"
                initialized["errors"].append(error_msg)
                print(f"Error adding {show}: {str(e)}")
        
        # Get final count
        final_count = await db.content.count_documents({})
        
        result = {
            **initialized,
            "total_items": final_count,
            "message": f"Content initialization completed. Total items: {final_count}"
        }
        
        print(f"Initialization complete: {initialized['movies']} movies, {initialized['series']} series, {initialized['skipped']} skipped, {len(initialized['errors'])} errors")
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
async def clear_content():
    """Clear all content from database"""
    try:
        result = await db.content.delete_many({})
        return {"message": f"Cleared {result.deleted_count} content items"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/force-reinitialize-content")
async def force_reinitialize_content():
    """Force reinitialize content by clearing and reloading"""
    try:
        # Clear existing content
        clear_result = await db.content.delete_many({})
        
        # Reinitialize
        init_result = await initialize_content()
        
        return {
            "cleared": clear_result.deleted_count,
            "reinitialized": init_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
async def initialize_content():
    """Initialize database with popular movies and TV shows"""
    try:
        # Check if content already exists
        existing_count = await db.content.count_documents({})
        if existing_count > 100:  # Only reinitialize if we have less than 100 items
            return {"message": f"Content already initialized with {existing_count} items"}
        
        initialized = {"movies": 0, "series": 0, "errors": [], "skipped": 0}
        
        # Process movies in batches to respect API limits
        print(f"Initializing {len(POPULAR_MOVIES)} movies...")
        for i, movie in enumerate(POPULAR_MOVIES):
            try:
                # Check if movie already exists
                existing_movie = await db.content.find_one({"title": movie, "content_type": "movie"})
                if existing_movie:
                    initialized["skipped"] += 1
                    continue
                    
                await search_and_store_content(movie, "movie")
                initialized["movies"] += 1
                print(f"Added movie {i+1}/{len(POPULAR_MOVIES)}: {movie}")
                
                # Small delay to be respectful to OMDB API
                if i % 10 == 0 and i > 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                error_msg = f"Movie {movie}: {str(e)}"
                initialized["errors"].append(error_msg)
                print(f"Error adding {movie}: {str(e)}")
        
        # Process TV shows in batches
        print(f"Initializing {len(POPULAR_TV_SHOWS)} TV shows...")
        for i, show in enumerate(POPULAR_TV_SHOWS):
            try:
                # Check if show already exists
                existing_show = await db.content.find_one({"title": show, "content_type": "series"})
                if existing_show:
                    initialized["skipped"] += 1
                    continue
                    
                await search_and_store_content(show, "series")
                initialized["series"] += 1
                print(f"Added TV show {i+1}/{len(POPULAR_TV_SHOWS)}: {show}")
                
                # Small delay to be respectful to OMDB API
                if i % 10 == 0 and i > 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                error_msg = f"Series {show}: {str(e)}"
                initialized["errors"].append(error_msg)
                print(f"Error adding {show}: {str(e)}")
        
        # Get final count
        final_count = await db.content.count_documents({})
        
        result = {
            **initialized,
            "total_items": final_count,
            "message": f"Content initialization completed. Total items: {final_count}"
        }
        
        print(f"Initialization complete: {initialized['movies']} movies, {initialized['series']} series, {initialized['skipped']} skipped, {len(initialized['errors'])} errors")
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/session")
async def create_session() -> UserSession:
    """Create a new guest session"""
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

@api_router.get("/voting-pair-replacement/{content_id}")
async def get_replacement_voting_pair(
    content_id: str,
    session_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
) -> VotePair:
    """Get a replacement item for voting pair (keeping one item, replacing the other)"""
    # Determine user identifier
    user_identifier = None
    if current_user:
        user_identifier = ("user", current_user.id)
    elif session_id:
        # Verify session exists
        session = await db.sessions.find_one({"session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        user_identifier = ("session", session_id)
    else:
        raise HTTPException(status_code=400, detail="Either login or provide session_id")
    
    # Get the content item that should remain
    remaining_content = await db.content.find_one({"id": content_id})
    if not remaining_content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Get items of the same type as the remaining content
    content_type = remaining_content["content_type"]
    items = await db.content.find({
        "content_type": content_type,
        "id": {"$ne": content_id}  # Exclude the remaining content
    }).to_list(length=None)
    
    if len(items) < 1:
        raise HTTPException(status_code=400, detail=f"Not enough {content_type} content available for replacement")
    
    # Get user's vote history to avoid showing same pairs
    if user_identifier[0] == "user":
        user_votes = await db.votes.find({"user_id": user_identifier[1]}).to_list(length=None)
    else:
        user_votes = await db.votes.find({"session_id": user_identifier[1]}).to_list(length=None)
    
    voted_pairs = set()
    for vote in user_votes:
        pair = frozenset([vote["winner_id"], vote["loser_id"]])
        voted_pairs.add(pair)
    
    # Find an unvoted pair with the remaining content
    max_attempts = 50
    for _ in range(max_attempts):
        replacement_item = random.choice(items)
        item_ids = frozenset([content_id, replacement_item["id"]])
        if item_ids not in voted_pairs:
            # Randomly decide which position the remaining content should be in
            if random.choice([True, False]):
                return VotePair(
                    item1=ContentItem(**remaining_content),
                    item2=ContentItem(**replacement_item),
                    content_type=content_type
                )
            else:
                return VotePair(
                    item1=ContentItem(**replacement_item),
                    item2=ContentItem(**remaining_content),
                    content_type=content_type
                )
    
    # If all pairs voted, return random replacement anyway
    replacement_item = random.choice(items)
    return VotePair(
        item1=ContentItem(**remaining_content),
        item2=ContentItem(**replacement_item),
        content_type=content_type
    )
@api_router.get("/voting-pair")
async def get_voting_pair(
    session_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
) -> VotePair:
    """Get a pair of items for voting (same content type only)"""
    # Determine user identifier
    user_identifier = None
    if current_user:
        user_identifier = ("user", current_user.id)
    elif session_id:
        # Verify session exists
        session = await db.sessions.find_one({"session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        user_identifier = ("session", session_id)
    else:
        raise HTTPException(status_code=400, detail="Either login or provide session_id")
    
    # Randomly choose content type (movie or series)
    content_type = random.choice(["movie", "series"])
    
    # Get items of the same type
    items = await db.content.find({"content_type": content_type}).to_list(length=None)
    
    if len(items) < 2:
        raise HTTPException(status_code=400, detail=f"Not enough {content_type} content available")
    
    # Get user's vote history to avoid showing same pairs
    if user_identifier[0] == "user":
        user_votes = await db.votes.find({"user_id": user_identifier[1]}).to_list(length=None)
    else:
        user_votes = await db.votes.find({"session_id": user_identifier[1]}).to_list(length=None)
    
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
async def submit_vote(
    vote_data: dict,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Submit a vote and update user/session"""
    required_fields = ["winner_id", "loser_id", "content_type"]
    for field in required_fields:
        if field not in vote_data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    
    # Determine user/session
    if current_user:
        # Logged in user
        vote = Vote(
            user_id=current_user.id,
            winner_id=vote_data["winner_id"],
            loser_id=vote_data["loser_id"],
            content_type=vote_data["content_type"]
        )
        
        await db.votes.insert_one(vote.dict())
        
        # Update user's total vote count
        await db.users.update_one(
            {"id": current_user.id},
            {"$inc": {"total_votes": 1}}
        )
        
        # Get updated user stats
        user_votes = await db.votes.find({"user_id": current_user.id}).to_list(length=None)
        total_votes = len(user_votes)
        
        # Automatically trigger recommendation generation in the background
        # when user reaches thresholds or has significant new activity
        if total_votes >= 10:
            try:
                # Check if we should auto-generate recommendations
                should_refresh = await check_and_auto_refresh_recommendations(current_user.id)
                is_milestone = total_votes in [10, 15, 20, 25, 30, 40, 50]
                
                if should_refresh or is_milestone:
                    # Run recommendation generation in background (fire and forget)
                    task = asyncio.create_task(auto_generate_ai_recommendations(current_user.id))
                    # Don't await the task - let it run in background
            except Exception as e:
                print(f"Background recommendation generation error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return {
            "vote_recorded": True,
            "total_votes": total_votes,
            "recommendations_available": total_votes >= 10,
            "user_authenticated": True
        }
    else:
        # Guest session
        if "session_id" not in vote_data:
            raise HTTPException(status_code=400, detail="Missing session_id for guest user")
        
        vote = Vote(
            session_id=vote_data["session_id"],
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
            "recommendations_available": session["vote_count"] >= 10,
            "user_authenticated": False
        }

@api_router.get("/recommendations")
async def get_recommendations(
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return"),
    session_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
) -> List[Recommendation]:
    """Get AI-powered recommendations with pagination support"""
    # For authenticated users, use advanced ML recommendations with auto-generation
    if current_user:
        try:
            # Get user votes to determine if they have enough data
            user_votes = await db.votes.find({"user_id": current_user.id}).to_list(length=None)
            
            # If user has insufficient data, fall back to simple recommendations
            if len(user_votes) < 10:
                return await get_simple_recommendations_fallback(user_votes)
            
            # Try to get existing AI recommendations first (with pagination)
            existing_recommendations = await get_stored_ai_recommendations(current_user.id, offset, limit)
            
            # If we have existing recommendations, check if they need refresh (only for first page)
            if existing_recommendations and offset == 0:
                should_refresh = await check_and_auto_refresh_recommendations(current_user.id)
                if should_refresh:
                    # Generate new recommendations but still return current page while generation happens
                    asyncio.create_task(auto_generate_ai_recommendations(current_user.id))
                return existing_recommendations
            elif existing_recommendations:
                # For subsequent pages, just return the stored recommendations
                return existing_recommendations
            
            # Generate new AI recommendations (either first time or refresh needed)
            if offset == 0:  # Only generate for first page request
                print(f"Generating recommendations for user {current_user.id} with {len(user_votes)} votes")
                await auto_generate_ai_recommendations(current_user.id)
                
                # Get the newly generated recommendations
                new_recommendations = await get_stored_ai_recommendations(current_user.id, offset, limit)
                if new_recommendations:
                    print(f"Successfully retrieved {len(new_recommendations)} stored recommendations for user {current_user.id}")
                    return new_recommendations
            
            # Fallback to real-time generation if storage fails (only for first page)
            if offset == 0:
                print(f"Storage failed, falling back to real-time generation for user {current_user.id}")
                return await generate_realtime_recommendations(current_user.id, limit)
            else:
                # For subsequent pages, return empty if no stored recommendations
                return []
            
        except Exception as e:
            print(f"Error in AI recommendations: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fall back to simple recommendations on error (only for first page)
            if offset == 0:
                user_votes = await db.votes.find({"user_id": current_user.id}).to_list(length=None)
                return await get_simple_recommendations_fallback(user_votes)
            else:
                return []
    
    # For guest users, use simple vote-based recommendations
    elif session_id:
        session = await db.sessions.find_one({"session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        user_votes = await db.votes.find({"session_id": session_id}).to_list(length=None)
        return await get_simple_recommendations_fallback(user_votes, offset, limit)
    else:
        raise HTTPException(status_code=400, detail="Either login or provide session_id")

async def check_and_auto_refresh_recommendations(user_id: str) -> bool:
    """Check if recommendations need automatic refresh"""
    try:
        # Get last recommendation generation time
        latest_rec = await db.algo_recommendations.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(1).to_list(length=1)
        
        if not latest_rec:
            return True  # No recommendations exist, need to generate
        
        last_rec_time = latest_rec[0]["created_at"]
        
        # Get recent interactions since last recommendation
        recent_interactions = await db.user_interactions.find({
            "user_id": user_id,
            "created_at": {"$gt": last_rec_time}
        }).to_list(length=None)
        
        recent_votes = await db.votes.find({
            "user_id": user_id,
            "created_at": {"$gt": last_rec_time}
        }).to_list(length=None)
        total_new_interactions = len(recent_interactions) + len(recent_votes)
        
        # Auto-refresh if user has 5+ new interactions or it's been 3+ days
        days_since_last = (datetime.utcnow() - last_rec_time).days
        
        refresh_needed = total_new_interactions >= 5 or days_since_last >= 3
        
        return refresh_needed
        
    except Exception as e:
        print(f"Error checking refresh need: {str(e)}")
        import traceback
        traceback.print_exc()
        return True  # Default to refresh on error

async def get_stored_ai_recommendations(user_id: str) -> List[Recommendation]:
    """Get stored AI recommendations from database"""
    try:
        # Get stored recommendations
        stored_recs = await db.algo_recommendations.find({
            "user_id": user_id,
            "viewed": False
        }).sort("recommendation_score", -1).limit(5).to_list(length=5)
        
        recommendations = []
        for rec in stored_recs:
            content = await db.content.find_one({"id": rec["content_id"]})
            if content:
                recommendations.append(Recommendation(
                    title=content["title"],
                    reason=rec["reasoning"],
                    poster=content.get("poster"),
                    imdb_id=content["imdb_id"]
                ))
        
        return recommendations
        
    except Exception as e:
        print(f"Error getting stored recommendations for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def auto_generate_ai_recommendations(user_id: str):
    """Automatically generate and store AI recommendations"""
    try:
        # Get all content for feature extraction
        all_content = await db.content.find().to_list(length=None)
        
        if not all_content:
            return
        
        # Extract content features
        content_df = recommendation_engine.extract_content_features(all_content)
        
        # Build user profile from interactions
        user_interactions = await db.user_interactions.find({"user_id": user_id}).to_list(length=None)
        
        # Also include vote data as interactions
        user_votes = await db.votes.find({"user_id": user_id}).to_list(length=None)
        
        # Convert votes to interactions
        for vote in user_votes:
            # Add winner interaction
            user_interactions.append({
                "content_id": vote["winner_id"],
                "interaction_type": "vote_winner",
                "created_at": vote["created_at"]
            })
            # Add loser interaction  
            user_interactions.append({
                "content_id": vote["loser_id"],
                "interaction_type": "vote_loser",
                "created_at": vote["created_at"]
            })
        
        # Add content details to interactions
        for interaction in user_interactions:
            content = await db.content.find_one({"id": interaction["content_id"]})
            if content:
                interaction["content"] = content
        
        # Build user profile
        user_profile = recommendation_engine.build_user_profile(user_interactions)
        
        # Get watched content IDs
        watched_interactions = await db.user_interactions.find({
            "user_id": user_id,
            "interaction_type": "watched"
        }).to_list(length=None)
        
        watched_content_ids = [i["content_id"] for i in watched_interactions]
        
        # Also exclude content user marked as "not_interested"
        not_interested = await db.user_interactions.find({
            "user_id": user_id,
            "interaction_type": "not_interested"
        }).to_list(length=None)
        
        watched_content_ids.extend([i["content_id"] for i in not_interested])
        
        # Generate recommendations
        ml_recommendations = recommendation_engine.generate_recommendations(
            user_profile, content_df, watched_content_ids, num_recommendations=10
        )
        
        if not ml_recommendations:
            return
        
        # Clear old recommendations
        await db.algo_recommendations.delete_many({"user_id": user_id})
        
        # Store new recommendations
        for rec in ml_recommendations:
            # Store in algo_recommendations
            algo_rec = AlgoRecommendation(
                user_id=user_id,
                content_id=rec["content_id"],
                recommendation_score=rec["score"],
                reasoning=rec["reasoning"],
                confidence=rec["confidence"]
            )
            await db.algo_recommendations.insert_one(algo_rec.dict())
        
        print(f"Auto-generated {len(ml_recommendations)} recommendations for user {user_id}")
        
    except Exception as e:
        print(f"Error auto-generating recommendations for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()

async def generate_realtime_recommendations(user_id: str) -> List[Recommendation]:
    """Generate recommendations in real-time as fallback"""
    try:
        # Get all content for feature extraction
        all_content = await db.content.find().to_list(length=None)
        
        if not all_content:
            return []
        
        # Extract content features
        content_df = recommendation_engine.extract_content_features(all_content)
        
        # Build user profile from interactions
        user_interactions = await db.user_interactions.find({"user_id": user_id}).to_list(length=None)
        
        # Also include vote data as interactions
        user_votes = await db.votes.find({"user_id": user_id}).to_list(length=None)
        
        # Convert votes to interactions
        for vote in user_votes:
            user_interactions.append({
                "content_id": vote["winner_id"],
                "interaction_type": "vote_winner",
                "created_at": vote["created_at"]
            })
            user_interactions.append({
                "content_id": vote["loser_id"],
                "interaction_type": "vote_loser",
                "created_at": vote["created_at"]
            })
        
        # Add content details to interactions
        for interaction in user_interactions:
            content = await db.content.find_one({"id": interaction["content_id"]})
            if content:
                interaction["content"] = content
        
        # Build user profile
        user_profile = recommendation_engine.build_user_profile(user_interactions)
        
        # Get watched content IDs
        watched_interactions = await db.user_interactions.find({
            "user_id": user_id,
            "interaction_type": "watched"
        }).to_list(length=None)
        
        watched_content_ids = [i["content_id"] for i in watched_interactions]
        
        # Also exclude content user marked as "not_interested"
        not_interested = await db.user_interactions.find({
            "user_id": user_id,
            "interaction_type": "not_interested"
        }).to_list(length=None)
        
        watched_content_ids.extend([i["content_id"] for i in not_interested])
        
        # Generate recommendations
        ml_recommendations = recommendation_engine.generate_recommendations(
            user_profile, content_df, watched_content_ids, num_recommendations=5
        )
        
        # Convert to API format
        recommendations = []
        for rec in ml_recommendations:
            content = await db.content.find_one({"id": rec["content_id"]})
            if content:
                recommendations.append(Recommendation(
                    title=content["title"],
                    reason=rec["reasoning"],
                    poster=content.get("poster"),
                    imdb_id=content["imdb_id"]
                ))
        
        return recommendations
        
    except Exception as e:
        print(f"Error generating realtime recommendations: {str(e)}")
        return []

async def get_simple_recommendations_fallback(user_votes: List[Dict]) -> List[Recommendation]:
    """Fallback to simple vote-based recommendations"""
    total_votes = len(user_votes)
    
    if total_votes < 10:  # Reduced from 36 for better UX
        return []
    
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

@api_router.get("/stats")
async def get_user_stats(
    session_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get user voting statistics"""
    if current_user:
        user_votes = await db.votes.find({"user_id": current_user.id}).to_list(length=None)
        total_votes = len(user_votes)
    elif session_id:
        session = await db.sessions.find_one({"session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        user_votes = await db.votes.find({"session_id": session_id}).to_list(length=None)
        total_votes = len(user_votes)
    else:
        raise HTTPException(status_code=400, detail="Either login or provide session_id")
    
    # Count by content type
    movie_votes = len([v for v in user_votes if v["content_type"] == "movie"])
    series_votes = len([v for v in user_votes if v["content_type"] == "series"])
    
    return {
        "total_votes": total_votes,
        "movie_votes": movie_votes,
        "series_votes": series_votes,
        "votes_until_recommendations": max(0, 10 - total_votes),
        "recommendations_available": total_votes >= 10,
        "user_authenticated": current_user is not None
    }

# Enhanced User Interaction Routes
@api_router.post("/content/interact")
async def content_interaction(
    interaction_data: dict,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Record user interaction with content (watched, want_to_watch, not_interested)"""
    required_fields = ["content_id", "interaction_type"]
    for field in required_fields:
        if field not in interaction_data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")
    
    # Validate interaction type
    valid_interactions = ["watched", "want_to_watch", "not_interested"]
    if interaction_data["interaction_type"] not in valid_interactions:
        raise HTTPException(status_code=400, detail="Invalid interaction type")
    
    # Create interaction record
    interaction = UserContentInteraction(
        user_id=current_user.id if current_user else None,
        session_id=interaction_data.get("session_id") if not current_user else None,
        content_id=interaction_data["content_id"],
        interaction_type=interaction_data["interaction_type"]
    )
    
    await db.user_interactions.insert_one(interaction.dict())
    
    # If "want_to_watch", also add to user watchlist
    if interaction_data["interaction_type"] == "want_to_watch" and current_user:
        # Check if already in watchlist
        existing = await db.user_watchlist.find_one({
            "user_id": current_user.id,
            "content_id": interaction_data["content_id"],
            "watchlist_type": "user_defined"
        })
        
        if not existing:
            watchlist_item = UserWatchlist(
                user_id=current_user.id,
                content_id=interaction_data["content_id"],
                priority=interaction_data.get("priority", 1),
                watchlist_type="user_defined"
            )
            await db.user_watchlist.insert_one(watchlist_item.dict())
    
    # Automatically trigger recommendation refresh for authenticated users
    # when they interact with content (important signal for ML algorithm)
    if current_user:
        try:
            # Get user's vote count to see if they qualify for recommendations
            user_votes = await db.votes.find({"user_id": current_user.id}).to_list(length=None)
            total_votes = len(user_votes)
            
            if total_votes >= 10:
                # Trigger background recommendation refresh on content interactions
                # since these are strong preference signals
                task = asyncio.create_task(auto_generate_ai_recommendations(current_user.id))
        except Exception as e:
            print(f"Background recommendation generation error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return {"success": True, "interaction_recorded": True}

@api_router.get("/watchlist/{watchlist_type}")
async def get_watchlist(
    watchlist_type: str,
    current_user: User = Depends(get_current_user)
):
    """Get user's watchlist (user_defined or algo_predicted)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if watchlist_type not in ["user_defined", "algo_predicted"]:
        raise HTTPException(status_code=400, detail="Invalid watchlist type")
    
    # Get watchlist items
    watchlist_items = await db.user_watchlist.find({
        "user_id": current_user.id,
        "watchlist_type": watchlist_type
    }).sort("added_at", -1).to_list(length=100)
    
    # Get content details for each item
    detailed_watchlist = []
    for item in watchlist_items:
        content = await db.content.find_one({"id": item["content_id"]})
        if content:
            detailed_item = {
                "watchlist_id": item["id"],
                "content": ContentItem(**content),
                "added_at": item["added_at"],
                "priority": item.get("priority", 1)
            }
            
            # For algo_predicted, add recommendation details
            if watchlist_type == "algo_predicted":
                algo_rec = await db.algo_recommendations.find_one({
                    "user_id": current_user.id,
                    "content_id": item["content_id"]
                })
                if algo_rec:
                    detailed_item.update({
                        "recommendation_score": algo_rec["recommendation_score"],
                        "reasoning": algo_rec["reasoning"],
                        "confidence": algo_rec["confidence"]
                    })
            
            detailed_watchlist.append(detailed_item)
    
    return {
        "watchlist_type": watchlist_type,
        "items": detailed_watchlist,
        "total_count": len(detailed_watchlist)
    }

@api_router.delete("/watchlist/{watchlist_id}")
async def remove_from_watchlist(
    watchlist_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove item from watchlist"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = await db.user_watchlist.delete_one({
        "id": watchlist_id,
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    return {"success": True, "removed": True}

@api_router.put("/watchlist/{watchlist_id}/priority")
async def update_watchlist_priority(
    watchlist_id: str,
    priority_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update watchlist item priority"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if "priority" not in priority_data or not isinstance(priority_data["priority"], int):
        raise HTTPException(status_code=400, detail="Valid priority (1-5) required")
    
    priority = max(1, min(5, priority_data["priority"]))  # Clamp to 1-5
    
    result = await db.user_watchlist.update_one(
        {"id": watchlist_id, "user_id": current_user.id},
        {"$set": {"priority": priority}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    return {"success": True, "priority_updated": True}

@api_router.get("/content/{content_id}/user-status")
async def get_content_user_status(
    content_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    session_id: Optional[str] = Query(None)
):
    """Get user's interaction status with specific content"""
    user_identifier = current_user.id if current_user else session_id
    
    if not user_identifier:
        return {"interactions": [], "in_watchlist": False}
    
    # Get user interactions
    query = {"content_id": content_id}
    if current_user:
        query["user_id"] = current_user.id
    else:
        query["session_id"] = session_id
    
    interactions = await db.user_interactions.find(query).to_list(length=None)
    
    # Check if in watchlist (only for authenticated users)
    in_watchlist = False
    watchlist_type = None
    if current_user:
        watchlist_item = await db.user_watchlist.find_one({
            "user_id": current_user.id,
            "content_id": content_id
        })
        if watchlist_item:
            in_watchlist = True
            watchlist_type = watchlist_item["watchlist_type"]
    
    return {
        "interactions": [i["interaction_type"] for i in interactions],
        "in_watchlist": in_watchlist,
        "watchlist_type": watchlist_type,
        "has_watched": "watched" in [i["interaction_type"] for i in interactions],
        "wants_to_watch": "want_to_watch" in [i["interaction_type"] for i in interactions],
        "not_interested": "not_interested" in [i["interaction_type"] for i in interactions]
    }
# Initialize ML Recommendation Engine
recommendation_engine = AdvancedRecommendationEngine()

# ML-Powered Recommendation Routes
@api_router.post("/recommendations/generate")
async def generate_ml_recommendations(
    current_user: User = Depends(get_current_user)
):
    """Generate ML-powered recommendations and store in algo_predicted watchlist"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Get all content for feature extraction
        all_content = await db.content.find().to_list(length=None)
        
        if not all_content:
            raise HTTPException(status_code=400, detail="No content available for recommendations")
        
        # Extract content features
        content_df = recommendation_engine.extract_content_features(all_content)
        
        # Build user profile from interactions
        user_interactions = await db.user_interactions.find({"user_id": current_user.id}).to_list(length=None)
        
        # Also include vote data as interactions
        user_votes = await db.votes.find({"user_id": current_user.id}).to_list(length=None)
        
        # Convert votes to interactions
        for vote in user_votes:
            # Add winner interaction
            user_interactions.append({
                "content_id": vote["winner_id"],
                "interaction_type": "vote_winner",
                "created_at": vote["created_at"]
            })
            # Add loser interaction  
            user_interactions.append({
                "content_id": vote["loser_id"],
                "interaction_type": "vote_loser",
                "created_at": vote["created_at"]
            })
        
        # Add content details to interactions
        for interaction in user_interactions:
            content = await db.content.find_one({"id": interaction["content_id"]})
            if content:
                interaction["content"] = content
        
        # Build user profile
        user_profile = recommendation_engine.build_user_profile(user_interactions)
        
        # Get watched content IDs
        watched_interactions = await db.user_interactions.find({
            "user_id": current_user.id,
            "interaction_type": "watched"
        }).to_list(length=None)
        
        watched_content_ids = [i["content_id"] for i in watched_interactions]
        
        # Also exclude content user marked as "not_interested"
        not_interested = await db.user_interactions.find({
            "user_id": current_user.id,
            "interaction_type": "not_interested"
        }).to_list(length=None)
        
        watched_content_ids.extend([i["content_id"] for i in not_interested])
        
        # Generate recommendations
        recommendations = recommendation_engine.generate_recommendations(
            user_profile, content_df, watched_content_ids, num_recommendations=15
        )
        
        if not recommendations:
            return {
                "message": "No new recommendations available. Try interacting with more content!",
                "recommendations_generated": 0
            }
        
        # Clear existing algo recommendations
        await db.algo_recommendations.delete_many({"user_id": current_user.id})
        await db.user_watchlist.delete_many({
            "user_id": current_user.id,
            "watchlist_type": "algo_predicted"
        })
        
        # Store recommendations
        stored_count = 0
        for rec in recommendations:
            # Store in algo_recommendations
            algo_rec = AlgoRecommendation(
                user_id=current_user.id,
                content_id=rec["content_id"],
                recommendation_score=rec["score"],
                reasoning=rec["reasoning"],
                confidence=rec["confidence"]
            )
            await db.algo_recommendations.insert_one(algo_rec.dict())
            
            # Add to algo_predicted watchlist
            watchlist_item = UserWatchlist(
                user_id=current_user.id,
                content_id=rec["content_id"],
                priority=min(5, max(1, int(rec["score"] * 5))),  # Convert score to 1-5 priority
                watchlist_type="algo_predicted"
            )
            await db.user_watchlist.insert_one(watchlist_item.dict())
            stored_count += 1
        
        return {
            "message": f"Generated {stored_count} personalized recommendations",
            "recommendations_generated": stored_count,
            "user_profile_strength": user_profile.get("preference_strength", 0.0),
            "recommendation_categories": {
                "high_confidence": len([r for r in recommendations if r["confidence"] > 0.7]),
                "medium_confidence": len([r for r in recommendations if 0.4 <= r["confidence"] <= 0.7]),
                "exploratory": len([r for r in recommendations if r["confidence"] < 0.4])
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")

@api_router.get("/recommendations/refresh-needed")
async def check_recommendations_refresh(
    current_user: User = Depends(get_current_user)
):
    """Check if user needs fresh recommendations based on recent activity"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get last recommendation generation time
    latest_rec = await db.algo_recommendations.find({
        "user_id": current_user.id
    }).sort("created_at", -1).limit(1).to_list(length=1)
    
    if not latest_rec:
        return {"refresh_needed": True, "reason": "No recommendations exist"}
    
    last_rec_time = latest_rec[0]["created_at"]
    
    # Get recent interactions since last recommendation
    recent_interactions = await db.user_interactions.find({
        "user_id": current_user.id,
        "created_at": {"$gt": last_rec_time}
    }).to_list(length=None)
    
    recent_votes = await db.votes.find({
        "user_id": current_user.id,
        "created_at": {"$gt": last_rec_time}
    }).to_list(length=None)
    
    total_new_interactions = len(recent_interactions) + len(recent_votes)
    
    # Refresh if user has 10+ new interactions or it's been 7+ days
    days_since_last = (datetime.utcnow() - last_rec_time).days
    
    refresh_needed = total_new_interactions >= 10 or days_since_last >= 7
    
    return {
        "refresh_needed": refresh_needed,
        "reason": f"{total_new_interactions} new interactions, {days_since_last} days old" if refresh_needed else "Recommendations are fresh",
        "new_interactions": total_new_interactions,
        "days_since_last": days_since_last
    }

@api_router.post("/recommendations/{rec_id}/action")
async def recommendation_user_action(
    rec_id: str,
    action_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Record user action on algorithmic recommendation"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    valid_actions = ["added_to_watchlist", "dismissed", "not_interested", "viewed"]
    action = action_data.get("action")
    
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    # Update recommendation record
    result = await db.algo_recommendations.update_one(
        {"id": rec_id, "user_id": current_user.id},
        {
            "$set": {
                "user_action": action,
                "viewed": True if action == "viewed" else False
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # If user is not interested, also record as interaction and remove from watchlist
    if action == "not_interested":
        rec = await db.algo_recommendations.find_one({"id": rec_id})
        if rec:
            # Record interaction
            interaction = UserContentInteraction(
                user_id=current_user.id,
                content_id=rec["content_id"],
                interaction_type="not_interested"
            )
            await db.user_interactions.insert_one(interaction.dict())
            
            # Remove from algo watchlist
            await db.user_watchlist.delete_one({
                "user_id": current_user.id,
                "content_id": rec["content_id"],
                "watchlist_type": "algo_predicted"
            })
    
    return {"success": True, "action_recorded": True}

@api_router.get("/profile/voting-history")
async def get_voting_history(current_user: User = Depends(get_current_user)):
    """Get user's detailed voting history"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_votes = await db.votes.find({"user_id": current_user.id}).sort("created_at", -1).to_list(length=100)
    
    history = []
    for vote in user_votes:
        winner = await db.content.find_one({"id": vote["winner_id"]})
        loser = await db.content.find_one({"id": vote["loser_id"]})
        
        if winner and loser:
            history.append({
                "id": vote["id"],
                "winner": {
                    "title": winner["title"],
                    "poster": winner.get("poster"),
                    "year": winner["year"]
                },
                "loser": {
                    "title": loser["title"],
                    "poster": loser.get("poster"),
                    "year": loser["year"]
                },
                "content_type": vote["content_type"],
                "voted_at": vote["created_at"]
            })
    
    return history

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
