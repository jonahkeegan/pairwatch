import requests
import unittest
import time
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
logger = logging.getLogger("watchlist_test")

class WatchlistAPITester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        self.test_results = []
        
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
                self.test_results.append({"name": name, "status": "PASS", "details": f"Status: {response.status_code}"})
            else:
                logger.error(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({"name": name, "status": "FAIL", "details": f"Expected {expected_status}, got {response.status_code}"})

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            logger.error(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({"name": name, "status": "ERROR", "details": str(e)})
            return False, {}

    def test_user_registration(self):
        """Test user registration"""
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
    
    def test_get_voting_pair(self):
        """Get a pair of items for voting"""
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False, {}
        
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=True
        )
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type):
        """Test submitting a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False, {}
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=True
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            logger.info(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_content_interaction(self, content_id, interaction_type):
        """Test content interaction (watched, want_to_watch, not_interested)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False, {}
        
        success, response = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=True
        )
        
        if success and response.get('success') == True:
            logger.info(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response

    def simulate_voting_to_threshold(self, target_votes=10):
        """Simulate voting until we reach the recommendation threshold"""
        logger.info(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes)...")
        
        # Get current vote count
        _, stats = self.run_test(
            "Get User Stats",
            "GET",
            "stats",
            200,
            auth=True
        )
        
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        logger.info(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair()
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type']
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                logger.info(f"Progress: {i+1}/{votes_needed} votes")
        
        logger.info(f"✅ Successfully completed {votes_needed} votes")
        return True

    def test_watchlist_endpoint(self):
        """Test the watchlist endpoint with pagination"""
        logger.info("\n🔍 TESTING WATCHLIST ENDPOINT")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Submit enough votes to enable recommendations
        logger.info("\n📋 Step 2: Submit enough votes to enable recommendations (10+ votes)")
        vote_success = self.simulate_voting_to_threshold(target_votes=10)
        if not vote_success:
            logger.error("❌ Failed to submit votes")
            return False
        
        # Step 3: Add a few items to the user's watchlist
        logger.info("\n📋 Step 3: Add a few items to the user's watchlist")
        
        # Get some content items to add to watchlist
        content_ids = []
        for _ in range(3):
            success, pair = self.test_get_voting_pair()
            if success:
                content_ids.append(pair['item1']['id'])
                content_ids.append(pair['item2']['id'])
        
        # Add items to watchlist
        added_count = 0
        for content_id in content_ids:
            success, _ = self.test_content_interaction(content_id, "want_to_watch")
            if success:
                added_count += 1
                logger.info(f"Added item {added_count} to watchlist")
            
            # Stop after adding 5 items
            if added_count >= 5:
                break
        
        logger.info(f"✅ Successfully added {added_count} items to watchlist")
        
        # Step 4: Test the watchlist endpoint
        logger.info("\n📋 Step 4: Test the watchlist endpoint with pagination")
        
        # Test with default parameters
        success, response = self.run_test(
            "Watchlist Default Parameters",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 0, "limit": 20}
        )
        
        if not success:
            logger.error("❌ Failed to get watchlist with default parameters")
            logger.error(f"Response: {response}")
            return False
        
        # Verify response structure
        if 'items' in response and 'total_count' in response:
            logger.info(f"✅ Watchlist contains {len(response['items'])} items")
            logger.info(f"✅ Total watchlist items: {response['total_count']}")
            
            # Log some details about the items
            for i, item in enumerate(response['items']):
                logger.info(f"  {i+1}. {item['content']['title']} - Added at: {item['added_at']}")
        else:
            logger.error("❌ Invalid response structure")
            logger.error(f"Response: {response}")
            return False
        
        # Test with different pagination parameters
        pagination_tests = [
            {"offset": 0, "limit": 2},
            {"offset": 2, "limit": 2},
            {"offset": 0, "limit": 10}
        ]
        
        for params in pagination_tests:
            success, response = self.run_test(
                f"Watchlist Pagination (offset={params['offset']}, limit={params['limit']})",
                "GET",
                "watchlist/user_defined",
                200,
                auth=True,
                params=params
            )
            
            if success and 'items' in response:
                logger.info(f"✅ Pagination with offset={params['offset']}, limit={params['limit']} returned {len(response['items'])} items")
            else:
                logger.error(f"❌ Failed pagination test with offset={params['offset']}, limit={params['limit']}")
                logger.error(f"Response: {response}")
        
        return True

def main():
    tester = WatchlistAPITester()
    tester.test_watchlist_endpoint()

if __name__ == "__main__":
    main()