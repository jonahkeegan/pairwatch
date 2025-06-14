import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("recommendation_test")

class RecommendationsAPITester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        
        # Test user credentials
        self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Test User {datetime.now().strftime('%H%M%S')}"
        
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

    def test_recommendations_structure(self):
        """Test the structure of recommendations response"""
        logger.info("\n🔍 TESTING RECOMMENDATIONS STRUCTURE")
        
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
        
        # Step 4: Examine recommendation structure
        logger.info("\n📋 Step 4: Examine recommendation structure")
        
        # Log the full structure of the first recommendation
        first_rec = recommendations[0]
        logger.info(f"First recommendation structure:")
        logger.info(json.dumps(first_rec, indent=2))
        
        # Check available fields
        available_fields = list(first_rec.keys())
        logger.info(f"Available fields: {available_fields}")
        
        # Check for ID fields
        id_fields = [field for field in available_fields if 'id' in field.lower()]
        logger.info(f"ID fields: {id_fields}")
        
        # Step 5: Try to mark content as watched using different ID fields
        logger.info("\n📋 Step 5: Try to mark content as watched using different ID fields")
        
        # Try with imdb_id if it exists
        if 'imdb_id' in first_rec:
            logger.info(f"Trying to mark content as watched using imdb_id: {first_rec['imdb_id']}")
            success, response = self.mark_content_as_watched(first_rec['imdb_id'])
            logger.info(f"Result using imdb_id: {'Success' if success else 'Failed'}")
            if not success:
                logger.info(f"Error response: {response}")
        
        # Try with id if it exists
        if 'id' in first_rec:
            logger.info(f"Trying to mark content as watched using id: {first_rec['id']}")
            success, response = self.mark_content_as_watched(first_rec['id'])
            logger.info(f"Result using id: {'Success' if success else 'Failed'}")
            if not success:
                logger.info(f"Error response: {response}")
        
        # Try with content_id if it exists
        if 'content_id' in first_rec:
            logger.info(f"Trying to mark content as watched using content_id: {first_rec['content_id']}")
            success, response = self.mark_content_as_watched(first_rec['content_id'])
            logger.info(f"Result using content_id: {'Success' if success else 'Failed'}")
            if not success:
                logger.info(f"Error response: {response}")
        
        # If none of the above fields exist, try to get content ID from database
        # This would require database access, which we don't have in this script
        
        # Step 6: Get more recommendations to check pagination
        logger.info("\n📋 Step 6: Get more recommendations to check pagination")
        success, more_recommendations = self.get_recommendations(offset=5, limit=5)
        
        if success and isinstance(more_recommendations, list):
            logger.info(f"Got {len(more_recommendations)} more recommendations")
            
            # Check if we got different recommendations
            if len(more_recommendations) > 0:
                first_batch_titles = [rec['title'] for rec in recommendations]
                second_batch_titles = [rec['title'] for rec in more_recommendations]
                
                duplicates = set(first_batch_titles) & set(second_batch_titles)
                if duplicates:
                    logger.warning(f"Found {len(duplicates)} duplicate recommendations between pages")
                else:
                    logger.info("No duplicate recommendations between pages")
        
        return True

if __name__ == "__main__":
    tester = RecommendationsAPITester()
    tester.test_recommendations_structure()