import requests
import unittest
import time
import sys
import random
import string
import uuid
from datetime import datetime
import json
import pymongo
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backend_api_test")

class MoviePreferenceAPITester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.auth_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
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
        
        self.tests_run += 1
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
                self.tests_passed += 1
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

    # Authentication Tests
    def test_user_registration(self):
        """Test user registration with various email formats"""
        # Generate a random email format
        email_formats = [
            f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
            f"test.user.{datetime.now().strftime('%Y%m%d%H%M%S')}@gmail.com",
            f"test-user-{datetime.now().strftime('%Y%m%d%H%M%S')}@company-name.co.uk",
            f"testuser{datetime.now().strftime('%Y%m%d%H%M%S')}@subdomain.domain.org"
        ]
        
        self.test_user_email = random.choice(email_formats)
        
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
    
    def test_user_login(self):
        """Test user login with correct credentials"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=data
        )
        
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            self.user_id = response['user']['id']
            logger.info(f"✅ User logged in with ID: {self.user_id}")
            logger.info(f"✅ Auth token received: {self.auth_token[:10]}...")
            return True, response
        
        return False, response
    
    def test_user_login_incorrect_credentials(self):
        """Test user login with incorrect credentials"""
        data = {
            "email": self.test_user_email,
            "password": "WrongPassword123!"
        }
        
        success, response = self.run_test(
            "User Login with Incorrect Password",
            "POST",
            "auth/login",
            401,  # Expecting 401 Unauthorized
            data=data
        )
        
        if success:
            logger.info("✅ Login correctly rejected with incorrect password")
            return True, response
        
        return False, response
    
    def test_protected_endpoint_with_valid_token(self):
        """Test protected endpoint with valid token"""
        if not self.auth_token:
            logger.error("❌ No auth token available")
            self.test_results.append({"name": "Protected Endpoint with Valid Token", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Protected Endpoint with Valid Token",
            "GET",
            "auth/me",
            200,
            auth=True
        )
        
        if success and 'id' in response and response['id'] == self.user_id:
            logger.info("✅ Protected endpoint accessible with valid token")
            return True, response
        
        return False, response
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test protected endpoint with invalid token"""
        # Save the real token temporarily
        real_token = self.auth_token
        
        # Set an invalid token
        self.auth_token = "invalid_token_123456789"
        
        success, response = self.run_test(
            "Protected Endpoint with Invalid Token",
            "GET",
            "auth/me",
            401,  # Expecting 401 Unauthorized
            auth=True
        )
        
        # Restore the real token
        self.auth_token = real_token
        
        if success:
            logger.info("✅ Protected endpoint correctly rejected invalid token")
            return True, response
        
        return False, response
    
    def test_create_session(self):
        """Test session creation for guest users"""
        success, response = self.run_test(
            "Create Session",
            "POST",
            "session",
            200,
            data={}
        )
        
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            logger.info(f"✅ Session created with ID: {self.session_id}")
            return True, response
        
        return False, response
    
    def test_get_voting_pair(self, use_auth=False):
        """Test voting pair endpoint for both guest sessions and authenticated users"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Voting Pair", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=auth,
            params=params
        )
        
        if success and 'item1' in response and 'item2' in response:
            # Check if poster URLs are present
            if response['item1'].get('poster') and response['item2'].get('poster'):
                logger.info(f"✅ Both items have poster URLs")
                logger.info(f"✅ Item 1 poster: {response['item1']['poster'][:50]}...")
                logger.info(f"✅ Item 2 poster: {response['item2']['poster'][:50]}...")
            else:
                logger.warning("⚠️ One or both items missing poster URLs")
                
            # Check if genres are populated
            if response['item1'].get('genre') and response['item2'].get('genre'):
                logger.info(f"✅ Both items have genres")
                logger.info(f"✅ Item 1 genre: {response['item1']['genre']}")
                logger.info(f"✅ Item 2 genre: {response['item2']['genre']}")
            else:
                logger.warning("⚠️ One or both items missing genres")
                
            # Check if ratings are populated
            if response['item1'].get('rating') and response['item2'].get('rating'):
                logger.info(f"✅ Both items have ratings")
                logger.info(f"✅ Item 1 rating: {response['item1']['rating']}")
                logger.info(f"✅ Item 2 rating: {response['item2']['rating']}")
            else:
                logger.warning("⚠️ One or both items missing ratings")
            
            return True, response
        
        return False, response
    
    def test_voting_pair_replacement(self, use_auth=False):
        """Test voting pair replacement endpoint"""
        # First, get a regular voting pair
        pair_success, pair = self.test_get_voting_pair(use_auth)
        if not pair_success:
            logger.error("❌ Failed to get initial voting pair")
            return False, {}
        
        # Get the content ID to keep
        content_id = pair['item1']['id']
        
        # Now test the replacement endpoint
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Voting Pair Replacement", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Voting Pair Replacement",
            "GET",
            f"voting-pair-replacement/{content_id}",
            200,
            auth=auth,
            params=params
        )
        
        if success and 'item1' in response and 'item2' in response:
            # Check if the requested content ID is in the response
            if response['item1']['id'] == content_id or response['item2']['id'] == content_id:
                logger.info(f"✅ Replacement pair contains the requested content ID: {content_id}")
            else:
                logger.error(f"❌ Replacement pair does not contain the requested content ID: {content_id}")
                return False, response
                
            # Check if poster URLs are present
            if response['item1'].get('poster') and response['item2'].get('poster'):
                logger.info(f"✅ Both items have poster URLs")
                logger.info(f"✅ Item 1 poster: {response['item1']['poster'][:50]}...")
                logger.info(f"✅ Item 2 poster: {response['item2']['poster'][:50]}...")
            else:
                logger.warning("⚠️ One or both items missing poster URLs")
            
            return True, response
        
        return False, response
    
    def test_submit_vote(self, winner_id, loser_id, content_type, use_auth=True):
        """Test submitting a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        if not use_auth or not self.auth_token:
            # Guest session vote
            if not self.session_id:
                logger.error("❌ No session ID available")
                self.test_results.append({"name": "Submit Vote", "status": "SKIP", "details": "No session ID available"})
                return False, {}
            data["session_id"] = self.session_id
            auth = False
        else:
            # Authenticated user vote
            auth = True
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=auth
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            logger.info(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response
    
    def test_content_interaction(self, content_id, interaction_type, use_auth=True, session_id=None):
        """Test content interaction (watched, want_to_watch, not_interested, passed)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif session_id or self.session_id:
            # Use guest session
            data["session_id"] = session_id or self.session_id
            auth = False
        else:
            logger.error("❌ No session ID or auth token available for content interaction")
            self.test_results.append({"name": f"Content Interaction ({interaction_type})", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=auth
        )
        
        if success and response.get('success') == True:
            logger.info(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response
    
    def test_pass_content(self, content_id, use_auth=True):
        """Test pass endpoint for marking content as passed"""
        data = {
            "content_id": content_id
        }
        
        if not use_auth or not self.auth_token:
            # Guest session
            if not self.session_id:
                logger.error("❌ No session ID available")
                self.test_results.append({"name": "Pass Content", "status": "SKIP", "details": "No session ID available"})
                return False, {}
            data["session_id"] = self.session_id
            auth = False
        else:
            # Authenticated user
            auth = True
        
        success, response = self.run_test(
            "Pass Content",
            "POST",
            "pass",
            200,
            data=data,
            auth=auth
        )
        
        if success and response.get('content_passed') == True:
            logger.info(f"✅ Content passed successfully")
            return True, response
        
        return False, response
    
    def test_get_stats(self, use_auth=True):
        """Test getting user stats"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Stats", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get User Stats",
            "GET",
            "stats",
            200,
            auth=auth,
            params=params
        )
        
        if success:
            logger.info(f"Total votes: {response.get('total_votes')}")
            logger.info(f"Movie votes: {response.get('movie_votes')}")
            logger.info(f"Series votes: {response.get('series_votes')}")
            logger.info(f"Votes until recommendations: {response.get('votes_until_recommendations')}")
            logger.info(f"Recommendations available: {response.get('recommendations_available')}")
            logger.info(f"User authenticated: {response.get('user_authenticated')}")
        
        return success, response
    
    def test_get_recommendations(self, use_auth=True, offset=0, limit=20):
        """Test getting recommendations"""
        params = {"offset": offset, "limit": limit}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params["session_id"] = self.session_id
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Recommendations", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Recommendations",
            "GET",
            "recommendations",
            200,
            auth=auth,
            params=params
        )
        
        if success and isinstance(response, list):
            logger.info(f"✅ Received {len(response)} recommendations")
            
            # Check for poster data in recommendations
            poster_count = 0
            for i, rec in enumerate(response):
                logger.info(f"  {i+1}. {rec.get('title')} - {rec.get('reason')}")
                
                if rec.get('poster'):
                    poster_count += 1
                    logger.info(f"    ✅ Has poster URL: {rec.get('poster')[:50]}...")
                else:
                    logger.info(f"    ⚠️ No poster available")
                    
                if rec.get('imdb_id'):
                    logger.info(f"    ✅ Has IMDB ID: {rec.get('imdb_id')}")
            
            logger.info(f"✅ {poster_count}/{len(response)} recommendations have poster images")
        
        return success, response
    
    def test_get_watchlist(self, use_auth=True, offset=0, limit=20):
        """Test getting user watchlist"""
        params = {"offset": offset, "limit": limit}
        
        if not use_auth or not self.auth_token:
            logger.error("❌ Watchlist requires authentication")
            self.test_results.append({"name": "Get Watchlist", "status": "SKIP", "details": "Watchlist requires authentication"})
            return False, {}
        
        success, response = self.run_test(
            "Get Watchlist",
            "GET",
            "watchlist/user_defined",
            200,
            auth=True,
            params=params
        )
        
        if success and 'items' in response:
            logger.info(f"✅ Received {len(response['items'])} watchlist items")
            logger.info(f"✅ Total watchlist items: {response.get('total_count')}")
            logger.info(f"✅ Has more items: {response.get('has_more')}")
            
            # Check a few items
            for i, item in enumerate(response['items'][:3]):
                if 'content' in item:
                    logger.info(f"  {i+1}. {item['content'].get('title')} - Priority: {item.get('priority')}")
                    
                    if item['content'].get('poster'):
                        logger.info(f"    ✅ Has poster URL: {item['content'].get('poster')[:50]}...")
                    else:
                        logger.info(f"    ⚠️ No poster available")
        
        return success, response
    
    def simulate_voting_to_threshold(self, use_auth=True, target_votes=10):
        """Simulate voting until we reach the recommendation threshold"""
        logger.info(f"\n🔄 Simulating votes to reach recommendation threshold ({target_votes} votes) using {'authenticated user' if use_auth else 'guest session'}...")
        
        # Get current vote count
        _, stats = self.test_get_stats(use_auth=use_auth)
        current_votes = stats.get('total_votes', 0)
        
        # Calculate how many more votes we need
        votes_needed = max(0, target_votes - current_votes)
        
        logger.info(f"Current votes: {current_votes}, Need {votes_needed} more to reach threshold of {target_votes}")
        
        for i in range(votes_needed):
            # Get a voting pair
            success, pair = self.test_get_voting_pair(use_auth)
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                return False
            
            # Submit a vote (always choose item1 as winner for simplicity)
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type'],
                use_auth
            )
            
            if not vote_success:
                logger.error(f"❌ Failed to submit vote on iteration {i+1}")
                return False
            
            # Print progress
            if (i+1) % 5 == 0 or i == votes_needed - 1:
                logger.info(f"Progress: {i+1}/{votes_needed} votes")
        
        logger.info(f"✅ Successfully completed {votes_needed} votes")
        return True
    
    def test_exclusion_functionality(self):
        """Test that content marked as watched/passed/not_interested is excluded from voting pairs"""
        logger.info("\n🔍 TESTING EXCLUSION FUNCTIONALITY")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Get a voting pair
        logger.info("\n📋 Step 2: Get a voting pair")
        pair_success, pair = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Step 3: Mark one item as "not_interested"
        logger.info("\n📋 Step 3: Mark one item as 'not_interested'")
        content_id = pair['item1']['id']
        content_title = pair['item1']['title']
        logger.info(f"Marking '{content_title}' (ID: {content_id}) as not_interested")
        
        interact_success, _ = self.test_content_interaction(content_id, "not_interested", use_auth=True)
        if not interact_success:
            logger.error("❌ Failed to mark content as not_interested")
            return False
        
        # Step 4: Get multiple voting pairs and verify the excluded content doesn't appear
        logger.info("\n📋 Step 4: Get multiple voting pairs and verify the excluded content doesn't appear")
        
        excluded_content_found = False
        test_iterations = 10
        
        for i in range(test_iterations):
            logger.info(f"Test iteration {i+1}/{test_iterations}")
            
            # Get a voting pair
            pair_success, new_pair = self.test_get_voting_pair(use_auth=True)
            if not pair_success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                continue
            
            # Check if the excluded content appears
            if new_pair['item1']['id'] == content_id or new_pair['item2']['id'] == content_id:
                logger.error(f"❌ Excluded content '{content_title}' (ID: {content_id}) found in voting pair!")
                excluded_content_found = True
                break
            else:
                logger.info(f"✅ Excluded content not found in voting pair {i+1}")
        
        if not excluded_content_found:
            logger.info(f"✅ Excluded content successfully excluded from {test_iterations} voting pairs")
            return True
        else:
            logger.error("❌ Excluded content found in voting pairs")
            return False
    
    def test_voting_pair_replacement_exclusion(self):
        """Test that content marked as watched/passed/not_interested is excluded from voting pair replacements"""
        logger.info("\n🔍 TESTING VOTING PAIR REPLACEMENT EXCLUSION FUNCTIONALITY")
        
        # Step 1: Register a new user if not already registered
        if not self.auth_token:
            logger.info("\n📋 Step 1: Register a new user")
            reg_success, _ = self.test_user_registration()
            if not reg_success:
                logger.error("❌ Failed to register user, stopping test")
                return False
        
        # Step 2: Get a voting pair
        logger.info("\n📋 Step 2: Get a voting pair")
        pair_success, pair = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Step 3: Mark one item as "not_interested"
        logger.info("\n📋 Step 3: Mark one item as 'not_interested'")
        excluded_content_id = pair['item1']['id']
        excluded_content_title = pair['item1']['title']
        logger.info(f"Marking '{excluded_content_title}' (ID: {excluded_content_id}) as not_interested")
        
        interact_success, _ = self.test_content_interaction(excluded_content_id, "not_interested", use_auth=True)
        if not interact_success:
            logger.error("❌ Failed to mark content as not_interested")
            return False
        
        # Step 4: Get another voting pair to use for replacement
        logger.info("\n📋 Step 4: Get another voting pair to use for replacement")
        pair_success, another_pair = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get another voting pair")
            return False
        
        # Step 5: Test replacement with multiple content items
        logger.info("\n📋 Step 5: Test replacement with multiple content items")
        
        excluded_content_found = False
        test_iterations = 10
        
        for i in range(test_iterations):
            # Get a content ID to keep
            content_id_to_keep = another_pair['item1']['id']
            
            # Test replacement
            logger.info(f"Test iteration {i+1}/{test_iterations} with content ID: {content_id_to_keep}")
            
            replacement_success, replacement_pair = self.run_test(
                f"Voting Pair Replacement {i+1}",
                "GET",
                f"voting-pair-replacement/{content_id_to_keep}",
                200,
                auth=True
            )
            
            if not replacement_success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if the excluded content appears
            if replacement_pair['item1']['id'] == excluded_content_id or replacement_pair['item2']['id'] == excluded_content_id:
                logger.error(f"❌ Excluded content '{excluded_content_title}' (ID: {excluded_content_id}) found in replacement pair!")
                excluded_content_found = True
                break
            else:
                logger.info(f"✅ Excluded content not found in replacement pair {i+1}")
            
            # Get another voting pair for the next iteration
            pair_success, another_pair = self.test_get_voting_pair(use_auth=True)
            if not pair_success:
                logger.error(f"❌ Failed to get another voting pair for iteration {i+1}")
                break
        
        if not excluded_content_found:
            logger.info(f"✅ Excluded content successfully excluded from {test_iterations} replacement pairs")
            return True
        else:
            logger.error("❌ Excluded content found in replacement pairs")
            return False
    
    def test_pass_functionality(self):
        """Test the pass functionality for marking content as passed"""
        logger.info("\n🔍 TESTING PASS FUNCTIONALITY")
        
        # Step 1: Register a new user if not already registered
        if not self.auth_token:
            logger.info("\n📋 Step 1: Register a new user")
            reg_success, _ = self.test_user_registration()
            if not reg_success:
                logger.error("❌ Failed to register user, stopping test")
                return False
        
        # Step 2: Get a voting pair
        logger.info("\n📋 Step 2: Get a voting pair")
        pair_success, pair = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Step 3: Mark one item as "passed"
        logger.info("\n📋 Step 3: Mark one item as 'passed'")
        content_id = pair['item1']['id']
        content_title = pair['item1']['title']
        logger.info(f"Marking '{content_title}' (ID: {content_id}) as passed")
        
        pass_success, pass_response = self.test_pass_content(content_id, use_auth=True)
        if not pass_success:
            logger.error("❌ Failed to mark content as passed")
            return False
        
        logger.info(f"✅ Content marked as passed: {pass_response}")
        
        # Step 4: Get multiple voting pairs and verify the passed content doesn't appear
        logger.info("\n📋 Step 4: Get multiple voting pairs and verify the passed content doesn't appear")
        
        passed_content_found = False
        test_iterations = 10
        
        for i in range(test_iterations):
            logger.info(f"Test iteration {i+1}/{test_iterations}")
            
            # Get a voting pair
            pair_success, new_pair = self.test_get_voting_pair(use_auth=True)
            if not pair_success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                continue
            
            # Check if the passed content appears
            if new_pair['item1']['id'] == content_id or new_pair['item2']['id'] == content_id:
                logger.error(f"❌ Passed content '{content_title}' (ID: {content_id}) found in voting pair!")
                passed_content_found = True
                break
            else:
                logger.info(f"✅ Passed content not found in voting pair {i+1}")
        
        if not passed_content_found:
            logger.info(f"✅ Passed content successfully excluded from {test_iterations} voting pairs")
            return True
        else:
            logger.error("❌ Passed content found in voting pairs")
            return False
    
    def test_invalid_session_id(self):
        """Test API behavior with invalid session ID"""
        logger.info("\n🔍 TESTING INVALID SESSION ID")
        
        # Generate an invalid session ID
        invalid_session_id = str(uuid.uuid4())
        
        # Test voting pair endpoint with invalid session ID
        success, response = self.run_test(
            "Voting Pair with Invalid Session ID",
            "GET",
            "voting-pair",
            404,  # Expecting 404 Not Found
            params={"session_id": invalid_session_id}
        )
        
        if success:
            logger.info("✅ Voting pair endpoint correctly rejected invalid session ID")
            return True, response
        
        return False, response
    
    def test_malformed_requests(self):
        """Test API behavior with malformed requests"""
        logger.info("\n🔍 TESTING MALFORMED REQUESTS")
        
        # Test 1: Missing required field in vote submission
        success1, _ = self.run_test(
            "Vote Submission with Missing Field",
            "POST",
            "vote",
            422,  # Expecting 422 Unprocessable Entity
            data={"winner_id": "some_id"}  # Missing loser_id and content_type
        )
        
        # Test 2: Invalid content type in vote submission
        if self.auth_token:
            success2, _ = self.run_test(
                "Vote Submission with Invalid Content Type",
                "POST",
                "vote",
                422,  # Expecting 422 Unprocessable Entity
                data={"winner_id": "some_id", "loser_id": "other_id", "content_type": "invalid_type"},
                auth=True
            )
        else:
            success2 = True  # Skip if no auth token
        
        # Test 3: Invalid JSON in request body
        success3 = False
        try:
            url = f"{self.base_url}/vote"
            headers = {'Content-Type': 'application/json'}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            # Send invalid JSON
            response = requests.post(url, data="this is not valid json", headers=headers)
            success3 = response.status_code in [400, 422]  # Expecting 400 Bad Request or 422 Unprocessable Entity
            
            logger.info(f"{'✅' if success3 else '❌'} Invalid JSON test: got status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Invalid JSON test error: {str(e)}")
        
        overall_success = success1 and success2 and success3
        if overall_success:
            logger.info("✅ All malformed request tests passed")
        else:
            logger.error("❌ Some malformed request tests failed")
        
        return overall_success
    
    def test_rate_limiting(self):
        """Test API rate limiting by making rapid requests"""
        logger.info("\n🔍 TESTING RATE LIMITING")
        
        # Make 20 rapid requests to the voting pair endpoint
        success_count = 0
        rate_limited = False
        
        for i in range(20):
            try:
                start_time = time.time()
                
                if self.session_id:
                    url = f"{self.base_url}/voting-pair?session_id={self.session_id}"
                    headers = {}
                elif self.auth_token:
                    url = f"{self.base_url}/voting-pair"
                    headers = {'Authorization': f'Bearer {self.auth_token}'}
                else:
                    logger.error("❌ No session ID or auth token available")
                    return False
                
                response = requests.get(url, headers=headers if self.auth_token else None)
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    success_count += 1
                    if i % 5 == 0:
                        logger.info(f"Request {i+1}: Success ({elapsed_time:.3f}s)")
                elif response.status_code == 429:  # Too Many Requests
                    rate_limited = True
                    logger.info(f"Request {i+1}: Rate limited ({elapsed_time:.3f}s)")
                    break
                else:
                    logger.warning(f"Request {i+1}: Unexpected status {response.status_code} ({elapsed_time:.3f}s)")
                
                # No delay between requests to test rate limiting
            except Exception as e:
                logger.error(f"Request {i+1} error: {str(e)}")
        
        logger.info(f"Made {success_count} successful requests out of 20 attempted")
        
        if rate_limited:
            logger.info("✅ Rate limiting detected")
        else:
            logger.info("✅ No rate limiting detected, all requests succeeded")
        
        return True  # Both outcomes are acceptable
    
    def run_all_tests(self):
        """Run all tests and return a summary"""
        logger.info("\n🔍 RUNNING ALL BACKEND TESTS")
        
        # Authentication Tests
        logger.info("\n=== AUTHENTICATION TESTS ===")
        self.test_user_registration()
        self.test_user_login()
        self.test_user_login_incorrect_credentials()
        self.test_protected_endpoint_with_valid_token()
        self.test_protected_endpoint_with_invalid_token()
        
        # Session Tests
        logger.info("\n=== SESSION TESTS ===")
        self.test_create_session()
        
        # Voting Pair Tests
        logger.info("\n=== VOTING PAIR TESTS ===")
        self.test_get_voting_pair(use_auth=True)  # Authenticated user
        self.test_get_voting_pair(use_auth=False)  # Guest session
        
        # Voting Pair Replacement Tests
        logger.info("\n=== VOTING PAIR REPLACEMENT TESTS ===")
        self.test_voting_pair_replacement(use_auth=True)  # Authenticated user
        self.test_voting_pair_replacement(use_auth=False)  # Guest session
        
        # Exclusion Functionality Tests
        logger.info("\n=== EXCLUSION FUNCTIONALITY TESTS ===")
        self.test_exclusion_functionality()
        self.test_voting_pair_replacement_exclusion()
        
        # Pass Functionality Tests
        logger.info("\n=== PASS FUNCTIONALITY TESTS ===")
        self.test_pass_functionality()
        
        # Edge Case Tests
        logger.info("\n=== EDGE CASE TESTS ===")
        self.test_invalid_session_id()
        self.test_malformed_requests()
        self.test_rate_limiting()
        
        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        logger.info(f"Total tests run: {self.tests_run}")
        logger.info(f"Tests passed: {self.tests_passed}")
        logger.info(f"Success rate: {(self.tests_passed / self.tests_run * 100):.2f}%")
        
        return self.tests_passed / self.tests_run

if __name__ == "__main__":
    tester = MoviePreferenceAPITester()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 0.9:  # 90% success rate threshold
        logger.info("✅ BACKEND TESTS PASSED")
        sys.exit(0)
    else:
        logger.error("❌ BACKEND TESTS FAILED")
        sys.exit(1)