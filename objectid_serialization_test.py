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
logger = logging.getLogger("objectid_serialization_test")

class ObjectIdSerializationTester:
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
                logger.error(f"Response: {response.text}")
                self.test_results.append({"name": name, "status": "FAIL", "details": f"Expected {expected_status}, got {response.status_code}"})

            try:
                return success, response.json() if response.text else {}
            except Exception as e:
                logger.error(f"❌ Failed to parse JSON response: {str(e)}")
                logger.error(f"Response text: {response.text}")
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

    def test_objectid_serialization(self):
        """Test the ObjectId serialization fix for the watchlist endpoint"""
        logger.info("\n🔍 TESTING OBJECTID SERIALIZATION FIX")
        
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
        
        # Step 3: Add items to the user's watchlist
        logger.info("\n📋 Step 3: Add items to the user's watchlist")
        
        # Get some content items to add to watchlist
        content_ids = []
        for _ in range(5):
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
            
            # Stop after adding 10 items
            if added_count >= 10:
                break
        
        logger.info(f"✅ Successfully added {added_count} items to watchlist")
        
        # Step 4: Test the watchlist endpoint with different pagination parameters
        logger.info("\n📋 Step 4: Test the watchlist endpoint with different pagination parameters")
        
        pagination_tests = [
            {"offset": 0, "limit": 5, "name": "First page"},
            {"offset": 5, "limit": 5, "name": "Second page"},
            {"offset": 0, "limit": 20, "name": "All items"}
        ]
        
        for test in pagination_tests:
            success, response = self.run_test(
                f"Watchlist {test['name']} (offset={test['offset']}, limit={test['limit']})",
                "GET",
                "watchlist/user_defined",
                200,
                auth=True,
                params={"offset": test['offset'], "limit": test['limit']}
            )
            
            if not success:
                logger.error(f"❌ Failed to get watchlist with offset={test['offset']}, limit={test['limit']}")
                return False
            
            # Verify response structure and content
            if 'items' in response and 'total_count' in response:
                logger.info(f"✅ {test['name']} contains {len(response['items'])} items")
                logger.info(f"✅ Total watchlist items: {response['total_count']}")
                logger.info(f"✅ Pagination metadata: offset={response['offset']}, limit={response['limit']}, has_more={response['has_more']}")
                
                # Check for expected fields in each item
                for i, item in enumerate(response['items'][:2]):  # Log first 2 items for brevity
                    logger.info(f"  {i+1}. {item['content']['title']} - Added at: {item['added_at']}")
                    
                    # Verify all required fields are present
                    required_fields = ['watchlist_id', 'content', 'added_at', 'priority']
                    missing_fields = [field for field in required_fields if field not in item]
                    
                    if missing_fields:
                        logger.error(f"❌ Item {i+1} is missing required fields: {missing_fields}")
                    else:
                        logger.info(f"  ✅ Item {i+1} has all required fields")
                    
                    # Verify content object has expected fields
                    content_fields = ['id', 'title', 'year', 'content_type', 'genre']
                    missing_content_fields = [field for field in content_fields if field not in item['content']]
                    
                    if missing_content_fields:
                        logger.error(f"❌ Content object for item {i+1} is missing fields: {missing_content_fields}")
                    else:
                        logger.info(f"  ✅ Content object for item {i+1} has all expected fields")
            else:
                logger.error("❌ Invalid response structure")
                logger.error(f"Response: {response}")
                return False
        
        # Step 5: Test edge cases
        logger.info("\n📋 Step 5: Test edge cases")
        
        # Test with invalid parameters
        invalid_params_tests = [
            {"offset": -1, "limit": 10, "expected_status": 422, "name": "Negative offset"},
            {"offset": 0, "limit": 0, "expected_status": 422, "name": "Zero limit"},
            {"offset": 0, "limit": 101, "expected_status": 422, "name": "Limit exceeding maximum"}
        ]
        
        for test in invalid_params_tests:
            success, response = self.run_test(
                f"Watchlist Invalid Parameters - {test['name']}",
                "GET",
                "watchlist/user_defined",
                test['expected_status'],
                auth=True,
                params={"offset": test['offset'], "limit": test['limit']}
            )
            
            if success:
                logger.info(f"✅ Correctly handled invalid parameters: {test['name']}")
            else:
                logger.error(f"❌ Failed to properly handle invalid parameters: {test['name']}")
        
        # Test with offset beyond available items
        success, response = self.run_test(
            "Watchlist Beyond Available Items",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params={"offset": 1000, "limit": 10}
        )
        
        if success and 'items' in response and len(response['items']) == 0:
            logger.info("✅ Correctly returned empty list for offset beyond available items")
        else:
            logger.error("❌ Failed to properly handle offset beyond available items")
        
        logger.info("\n✅ OBJECTID SERIALIZATION TEST COMPLETED SUCCESSFULLY")
        return True

def main():
    tester = ObjectIdSerializationTester()
    tester.test_objectid_serialization()

if __name__ == "__main__":
    main()