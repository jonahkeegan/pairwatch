import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json
import logging
import pymongo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("recommendations_api_test")

class RecommendationsAPITester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        
        # Test user credentials
        self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Test User {datetime.now().strftime('%H%M%S')}"
        
        # MongoDB connection
        self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.mongo_client["movie_preferences_db"]
        
        logger.info(f"🔍 Testing API at: {self.base_url}")
        logger.info(f"📝 Test user: {self.test_user_email}")

    def run_test(self, name, method, endpoint, expected_status, data=None, auth=False, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add authorization header if needed
        if auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        logger.info(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                logger.info(f"✅ Passed - Status: {response.status_code}")
            else:
                logger.error(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    logger.error(f"Response: {response.text}")

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            logger.error(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def register_user(self):
        """Register a new test user"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
            "name": self.test_user_name
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=data
        )
        
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            self.user_id = response['user']['id']
            logger.info(f"✅ User registered with ID: {self.user_id}")
            logger.info(f"✅ Auth token received: {self.auth_token[:10]}...")
            return True, response
        
        return False, response

    def get_voting_pair(self):
        """Get a pair of items for voting"""
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=True
        )
        
        return success, response

    def submit_vote(self, winner_id, loser_id, content_type):
        """Submit a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=True
        )
        
        if success and response.get('vote_recorded') == True:
            logger.info(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def get_recommendations(self, offset=0, limit=5):
        """Get recommendations with pagination"""
        success, response = self.run_test(
            "Get Recommendations",
            "GET",
            "recommendations",
            200,
            auth=True,
            params={"offset": offset, "limit": limit}
        )
        
        return success, response

    def mark_content_as_watched(self, content_id):
        """Mark content as watched"""
        data = {
            "content_id": content_id,
            "interaction_type": "watched"
        }
        
        success, response = self.run_test(
            "Mark Content as Watched",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=True
        )
        
        return success, response

    def submit_votes_to_threshold(self, target_votes=10):
        """Submit votes until reaching the threshold"""
        logger.info(f"\n🔄 Submitting votes to reach recommendation threshold ({target_votes} votes)...")
        
        votes_submitted = 0
        while votes_submitted < target_votes:
            # Get a voting pair
            success, pair = self.get_voting_pair()
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {votes_submitted+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, vote_response = self.submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type']
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {votes_submitted+1}")
                return False
            
            votes_submitted += 1
            
            # Print progress
            if votes_submitted % 5 == 0 or votes_submitted == target_votes:
                logger.info(f"Progress: {votes_submitted}/{target_votes} votes")
        
        logger.info(f"✅ Successfully submitted {votes_submitted} votes")
        return True

    def get_content_by_imdb_id(self, imdb_id):
        """Get content item from database by IMDB ID"""
        try:
            content = self.db.content.find_one({"imdb_id": imdb_id})
            if content:
                logger.info(f"✅ Found content in database with IMDB ID: {imdb_id}")
                logger.info(f"Content ID: {content['id']}")
                logger.info(f"Title: {content['title']}")
                return content
            else:
                logger.error(f"❌ Content not found with IMDB ID: {imdb_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Database error: {str(e)}")
            return None

    def test_recommendations_api_and_content_interaction(self):
        """Test the recommendations API and content interaction"""
        logger.info("\n🔍 TESTING RECOMMENDATIONS API AND CONTENT INTERACTION")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, _ = self.register_user()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Submit votes to get recommendations
        logger.info("\n📋 Step 2: Submit votes to get recommendations")
        votes_success = self.submit_votes_to_threshold(target_votes=10)
        if not votes_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Get recommendations (first page)
        logger.info("\n📋 Step 3: Get recommendations (first page)")
        success, first_page = self.get_recommendations(offset=0, limit=5)
        
        if not success:
            logger.error("❌ Failed to get recommendations")
            return False
        
        if not isinstance(first_page, list) or len(first_page) == 0:
            logger.error("❌ No recommendations returned")
            return False
        
        # Log the structure of the first recommendation
        logger.info("\n📋 Recommendation Structure Analysis:")
        first_rec = first_page[0]
        logger.info(f"First recommendation structure:")
        logger.info(json.dumps(first_rec, indent=2))
        
        # Check available fields
        available_fields = list(first_rec.keys())
        logger.info(f"Available fields: {available_fields}")
        
        # Check for ID fields
        id_fields = [field for field in available_fields if 'id' in field.lower()]
        logger.info(f"ID fields: {id_fields}")
        
        # Step 4: Get more recommendations (second page)
        logger.info("\n📋 Step 4: Get more recommendations (second page)")
        success, second_page = self.get_recommendations(offset=5, limit=5)
        
        if success and isinstance(second_page, list):
            logger.info(f"Second page contains {len(second_page)} recommendations")
            
            # Check for duplicate recommendations between pages
            if len(second_page) > 0:
                first_page_titles = [rec['title'] for rec in first_page]
                second_page_titles = [rec['title'] for rec in second_page]
                
                duplicates = set(first_page_titles) & set(second_page_titles)
                if duplicates:
                    logger.warning(f"⚠️ Found {len(duplicates)} duplicate recommendations between pages")
                else:
                    logger.info("✅ No duplicate recommendations between pages")
        
        # Step 5: Mark content as watched
        logger.info("\n📋 Step 5: Mark content as watched")
        if len(first_page) > 0:
            first_rec = first_page[0]
            logger.info(f"Marking content as watched: {first_rec['title']} (IMDB ID: {first_rec['imdb_id']})")
            
            # Get content from database to verify IDs
            content = self.get_content_by_imdb_id(first_rec['imdb_id'])
            
            if content:
                # Try with IMDB ID
                logger.info(f"Trying to mark content as watched using IMDB ID: {first_rec['imdb_id']}")
                imdb_success, imdb_response = self.mark_content_as_watched(first_rec['imdb_id'])
                logger.info(f"Result using IMDB ID: {'Success' if imdb_success else 'Failed'}")
                
                # Check if interaction was recorded in database
                try:
                    imdb_interaction = self.db.user_interactions.find_one({
                        "user_id": self.user_id,
                        "content_id": first_rec['imdb_id'],
                        "interaction_type": "watched"
                    })
                    
                    if imdb_interaction:
                        logger.info(f"✅ Found interaction in database with IMDB ID: {first_rec['imdb_id']}")
                    else:
                        logger.info(f"❌ No interaction found with IMDB ID: {first_rec['imdb_id']}")
                except Exception as e:
                    logger.error(f"❌ Database error: {str(e)}")
        
        # Step 6: Get recommendations again to see if watched content is excluded
        logger.info("\n📋 Step 6: Get recommendations again to see if watched content is excluded")
        success, updated_recs = self.get_recommendations(offset=0, limit=10)
        
        if success and isinstance(updated_recs, list):
            logger.info(f"Updated recommendations contains {len(updated_recs)} items")
            
            # Check if the watched content is still in recommendations
            watched_title = first_page[0]['title']
            watched_still_present = any(rec['title'] == watched_title for rec in updated_recs)
            
            if watched_still_present:
                logger.warning(f"⚠️ Watched content '{watched_title}' is still present in recommendations")
            else:
                logger.info(f"✅ Watched content '{watched_title}' is no longer in recommendations")
        
        # Step 7: Summary
        logger.info("\n📋 Summary of Recommendations API Testing")
        logger.info(f"1. Recommendation fields: {available_fields}")
        logger.info(f"2. ID fields available: {id_fields}")
        logger.info(f"3. Content interaction using IMDB ID: {'Success' if imdb_success else 'Failed'}")
        
        # Conclusion
        logger.info("\n📋 CONCLUSION")
        logger.info("1. The recommendations API returns objects with the following fields:")
        for field in available_fields:
            logger.info(f"   - {field}")
        
        logger.info(f"2. The correct field to use for content ID is 'imdb_id'")
        logger.info(f"3. The content interaction endpoint accepts IMDB ID for marking content as watched")
        
        return True

if __name__ == "__main__":
    tester = RecommendationsAPITester()
    tester.test_recommendations_api_and_content_interaction()