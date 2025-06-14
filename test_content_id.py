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
logger = logging.getLogger("content_id_test")

class ContentIDTester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
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

    def test_content_id_for_interaction(self):
        """Test which content ID format is expected for content interaction"""
        logger.info("\n🔍 TESTING CONTENT ID FORMAT FOR INTERACTION")
        
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
        
        # Step 3: Get recommendations
        logger.info("\n📋 Step 3: Get recommendations")
        success, recommendations = self.get_recommendations(offset=0, limit=5)
        
        if not success:
            logger.error("❌ Failed to get recommendations")
            return False
        
        if not isinstance(recommendations, list) or len(recommendations) == 0:
            logger.error("❌ No recommendations returned")
            return False
        
        # Step 4: Get the first recommendation
        first_rec = recommendations[0]
        logger.info(f"First recommendation: {first_rec['title']} (IMDB ID: {first_rec['imdb_id']})")
        
        # Step 5: Get content from database using IMDB ID
        logger.info("\n📋 Step 5: Get content from database using IMDB ID")
        imdb_id = first_rec['imdb_id']
        content = self.get_content_by_imdb_id(imdb_id)
        
        if not content:
            logger.error("❌ Failed to get content from database")
            return False
        
        content_id = content['id']
        
        # Step 6: Try to mark content as watched using IMDB ID
        logger.info("\n📋 Step 6: Try to mark content as watched using IMDB ID")
        imdb_success, imdb_response = self.mark_content_as_watched(imdb_id)
        
        logger.info(f"Result using IMDB ID: {'Success' if imdb_success else 'Failed'}")
        if not imdb_success:
            logger.info(f"Error response: {imdb_response}")
        
        # Step 7: Try to mark content as watched using content ID from database
        logger.info("\n📋 Step 7: Try to mark content as watched using content ID from database")
        content_success, content_response = self.mark_content_as_watched(content_id)
        
        logger.info(f"Result using content ID: {'Success' if content_success else 'Failed'}")
        if not content_success:
            logger.info(f"Error response: {content_response}")
        
        # Step 8: Check if interactions were recorded in database
        logger.info("\n📋 Step 8: Check if interactions were recorded in database")
        try:
            # Check for interaction with IMDB ID
            imdb_interaction = self.db.user_interactions.find_one({
                "user_id": self.user_id,
                "content_id": imdb_id,
                "interaction_type": "watched"
            })
            
            if imdb_interaction:
                logger.info(f"✅ Found interaction in database with IMDB ID: {imdb_id}")
            else:
                logger.info(f"❌ No interaction found with IMDB ID: {imdb_id}")
            
            # Check for interaction with content ID
            content_interaction = self.db.user_interactions.find_one({
                "user_id": self.user_id,
                "content_id": content_id,
                "interaction_type": "watched"
            })
            
            if content_interaction:
                logger.info(f"✅ Found interaction in database with content ID: {content_id}")
            else:
                logger.info(f"❌ No interaction found with content ID: {content_id}")
            
        except Exception as e:
            logger.error(f"❌ Database error: {str(e)}")
        
        # Step 9: Try with a second recommendation to confirm
        logger.info("\n📋 Step 9: Try with a second recommendation to confirm")
        if len(recommendations) > 1:
            second_rec = recommendations[1]
            logger.info(f"Second recommendation: {second_rec['title']} (IMDB ID: {second_rec['imdb_id']})")
            
            second_imdb_id = second_rec['imdb_id']
            second_content = self.get_content_by_imdb_id(second_imdb_id)
            
            if second_content:
                second_content_id = second_content['id']
                
                # Try with the ID that worked in the first test
                if imdb_success and not content_success:
                    logger.info(f"Trying second recommendation with IMDB ID: {second_imdb_id}")
                    success, response = self.mark_content_as_watched(second_imdb_id)
                    logger.info(f"Result: {'Success' if success else 'Failed'}")
                elif content_success and not imdb_success:
                    logger.info(f"Trying second recommendation with content ID: {second_content_id}")
                    success, response = self.mark_content_as_watched(second_content_id)
                    logger.info(f"Result: {'Success' if success else 'Failed'}")
                else:
                    # If both worked or both failed, try both again
                    logger.info(f"Trying second recommendation with IMDB ID: {second_imdb_id}")
                    imdb_success, _ = self.mark_content_as_watched(second_imdb_id)
                    logger.info(f"Result: {'Success' if imdb_success else 'Failed'}")
                    
                    logger.info(f"Trying second recommendation with content ID: {second_content_id}")
                    content_success, _ = self.mark_content_as_watched(second_content_id)
                    logger.info(f"Result: {'Success' if content_success else 'Failed'}")
        
        # Step 10: Summary
        logger.info("\n📋 Step 10: Summary")
        if imdb_success and not content_success:
            logger.info("✅ CONCLUSION: The API expects the IMDB ID for content interaction")
        elif content_success and not imdb_success:
            logger.info("✅ CONCLUSION: The API expects the content ID for content interaction")
        elif imdb_success and content_success:
            logger.info("✅ CONCLUSION: The API accepts both IMDB ID and content ID for content interaction")
        else:
            logger.info("❓ CONCLUSION: Neither IMDB ID nor content ID worked for content interaction")
        
        return True

if __name__ == "__main__":
    tester = ContentIDTester()
    tester.test_content_id_for_interaction()