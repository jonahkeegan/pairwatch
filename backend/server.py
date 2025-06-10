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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[User]:
    """Get current user from JWT token"""
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except jwt.ExpiredSignatureToken:
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
        
        return {
            "vote_recorded": True,
            "total_votes": total_votes,
            "recommendations_available": total_votes >= 36,
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
            "recommendations_available": session["vote_count"] >= 36,
            "user_authenticated": False
        }

@api_router.get("/recommendations")
async def get_recommendations(
    session_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
) -> List[Recommendation]:
    """Get recommendations based on voting history"""
    # Get user votes
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
    
    if total_votes < 36:
        raise HTTPException(status_code=400, detail="Need at least 36 votes for recommendations")
    
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
        "votes_until_recommendations": max(0, 36 - total_votes),
        "recommendations_available": total_votes >= 36,
        "user_authenticated": current_user is not None
    }

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
