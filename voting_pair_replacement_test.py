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
logger = logging.getLogger("voting_pair_replacement_test")

class VotingPairReplacementTester:
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
    
    def test_user_login(self, email=None, password=None):
        """Test user login"""
        data = {
            "email": email or self.test_user_email,
            "password": password or self.test_user_password
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
    
    def test_get_voting_pair(self, use_auth=False):
        """Get a pair of items for voting"""
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
        
        return success, response

    def test_get_replacement_voting_pair(self, content_id, use_auth=False):
        """Get a replacement voting pair for a specific content ID"""
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
            self.test_results.append({"name": "Get Replacement Voting Pair", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Get Replacement Voting Pair for {content_id}",
            "GET",
            f"voting-pair-replacement/{content_id}",
            200,
            auth=auth,
            params=params
        )
        
        return success, response

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
        """Test passing on content during voting"""
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
            logger.info(f"✅ Content passed successfully: {content_id}")
            return True, response
        
        return success, response

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

    def test_voting_pair_replacement_with_excluded_content(self):
        """
        Test the voting-pair-replacement endpoint to verify that content marked as 
        "not_interested" or "passed" is permanently excluded from replacement pairs.
        """
        logger.info("\n🔍 TESTING VOTING PAIR REPLACEMENT WITH EXCLUDED CONTENT")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Get some initial voting pairs to find content to exclude
        logger.info("\n📋 Step 2: Get initial voting pairs to find content to exclude")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Record the content IDs for later verification
        content_to_keep = pair['item1']
        content_to_exclude = pair['item2']
        
        logger.info(f"Content to keep: {content_to_keep['title']} (ID: {content_to_keep['id']})")
        logger.info(f"Content to exclude: {content_to_exclude['title']} (ID: {content_to_exclude['id']})")
        
        # Step 3: Mark the content as "not_interested"
        logger.info("\n📋 Step 3: Mark content as 'not_interested'")
        success, _ = self.test_content_interaction(
            content_to_exclude['id'], 
            "not_interested", 
            use_auth=True
        )
        if not success:
            logger.error("❌ Failed to mark content as not_interested")
            return False
        
        # Step 4: Test the replacement endpoint multiple times to verify exclusion
        logger.info("\n📋 Step 4: Test replacement endpoint multiple times to verify exclusion")
        excluded_content_found = False
        
        for i in range(10):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                content_to_keep['id'], 
                use_auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if the excluded content appears in the replacement pair
            replacement_ids = [
                replacement_pair['item1']['id'],
                replacement_pair['item2']['id']
            ]
            
            if content_to_exclude['id'] in replacement_ids:
                excluded_content_found = True
                logger.error(f"❌ Excluded content found in replacement pair on iteration {i+1}")
                break
            
            logger.info(f"✅ Iteration {i+1}: Excluded content not found in replacement pair")
        
        if not excluded_content_found:
            logger.info("✅ Excluded content was properly excluded from all replacement pairs")
        
        # Step 5: Get another voting pair and test with "passed" content
        logger.info("\n📋 Step 5: Get another voting pair and test with 'passed' content")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Record the content IDs for later verification
        content_to_keep2 = pair['item1']
        content_to_pass = pair['item2']
        
        logger.info(f"Content to keep: {content_to_keep2['title']} (ID: {content_to_keep2['id']})")
        logger.info(f"Content to pass: {content_to_pass['title']} (ID: {content_to_pass['id']})")
        
        # Step 6: Pass on the content
        logger.info("\n📋 Step 6: Pass on content")
        success, _ = self.test_pass_content(
            content_to_pass['id'], 
            use_auth=True
        )
        if not success:
            logger.error("❌ Failed to pass on content")
            return False
        
        # Step 7: Test the replacement endpoint multiple times to verify exclusion
        logger.info("\n📋 Step 7: Test replacement endpoint multiple times to verify exclusion of passed content")
        passed_content_found = False
        
        for i in range(10):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                content_to_keep2['id'], 
                use_auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if the passed content appears in the replacement pair
            replacement_ids = [
                replacement_pair['item1']['id'],
                replacement_pair['item2']['id']
            ]
            
            if content_to_pass['id'] in replacement_ids:
                passed_content_found = True
                logger.error(f"❌ Passed content found in replacement pair on iteration {i+1}")
                break
            
            logger.info(f"✅ Iteration {i+1}: Passed content not found in replacement pair")
        
        if not passed_content_found:
            logger.info("✅ Passed content was properly excluded from all replacement pairs")
        
        # Step 8: Test with multiple excluded content items
        logger.info("\n📋 Step 8: Test with multiple excluded content items")
        
        # Get more voting pairs and exclude them
        excluded_items = []
        for i in range(5):
            success, pair = self.test_get_voting_pair(use_auth=True)
            if not success:
                continue
            
            # Alternate between not_interested and passed
            interaction_type = "not_interested" if i % 2 == 0 else "passed"
            content_to_exclude = pair['item2']
            
            if interaction_type == "not_interested":
                success, _ = self.test_content_interaction(
                    content_to_exclude['id'], 
                    interaction_type, 
                    use_auth=True
                )
            else:
                success, _ = self.test_pass_content(
                    content_to_exclude['id'], 
                    use_auth=True
                )
            
            if success:
                excluded_items.append({
                    "id": content_to_exclude['id'],
                    "title": content_to_exclude['title'],
                    "type": interaction_type
                })
                logger.info(f"Marked content as {interaction_type}: {content_to_exclude['title']} (ID: {content_to_exclude['id']})")
        
        logger.info(f"Excluded {len(excluded_items)} additional content items")
        
        # Step 9: Test the replacement endpoint with a new base content item
        logger.info("\n📋 Step 9: Test replacement endpoint with a new base content item")
        
        # Get a new voting pair to use as base
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        base_content = pair['item1']
        logger.info(f"Base content for replacement: {base_content['title']} (ID: {base_content['id']})")
        
        # Test multiple replacements
        any_excluded_found = False
        for i in range(10):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                base_content['id'], 
                use_auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if any excluded content appears in the replacement pair
            replacement_ids = [
                replacement_pair['item1']['id'],
                replacement_pair['item2']['id']
            ]
            
            for excluded_item in excluded_items:
                if excluded_item['id'] in replacement_ids:
                    any_excluded_found = True
                    logger.error(f"❌ Excluded content '{excluded_item['title']}' ({excluded_item['type']}) found in replacement pair on iteration {i+1}")
                    break
            
            if not any_excluded_found:
                logger.info(f"✅ Iteration {i+1}: No excluded content found in replacement pair")
            else:
                break
        
        if not any_excluded_found:
            logger.info("✅ All excluded content was properly excluded from all replacement pairs")
        
        # Step 10: Test with the specific user and content from the bug report
        logger.info("\n📋 Step 10: Test with the specific user and content from the bug report")
        
        # Log out current user
        self.auth_token = None
        self.user_id = None
        
        # Log in as test009@yopmail.com
        success, _ = self.test_user_login("test009@yopmail.com", "password123")
        if not success:
            logger.error("❌ Failed to log in as test009@yopmail.com")
            return False
        
        # The specific content ID from the bug report
        leonardo_content_id = "1d26e225-a9b5-4ff9-9eb4-c6ba117f240b"
        
        # Check if this content exists in the database
        leonardo_content = self.db.content.find_one({"id": leonardo_content_id})
        if not leonardo_content:
            logger.warning("⚠️ Leonardo DiCaprio content not found in database with that ID, will use a different content item for testing")
            
            # Try to find a Leonardo DiCaprio movie
            leonardo_movies = list(self.db.content.find({"title": {"$regex": "Leonardo DiCaprio", "$options": "i"}}))
            if leonardo_movies:
                leonardo_content_id = leonardo_movies[0]["id"]
                logger.info(f"Found alternative Leonardo DiCaprio content: {leonardo_movies[0]['title']} (ID: {leonardo_content_id})")
            else:
                # Just get any content item to continue testing
                random_content = list(self.db.content.find().limit(1))[0]
                leonardo_content_id = random_content["id"]
                logger.info(f"Using random content for testing: {random_content['title']} (ID: {leonardo_content_id})")
        
        # Mark the Leonardo content as "not_interested"
        success, _ = self.test_content_interaction(
            leonardo_content_id, 
            "not_interested", 
            use_auth=True
        )
        if not success:
            logger.error("❌ Failed to mark Leonardo content as not_interested")
            return False
        
        # Get a base content item for replacement testing
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        base_content = pair['item1']
        
        # Test multiple replacements to verify Leonardo content is excluded
        leonardo_found = False
        for i in range(20):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                base_content['id'], 
                use_auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if Leonardo content appears in the replacement pair
            replacement_ids = [
                replacement_pair['item1']['id'],
                replacement_pair['item2']['id']
            ]
            
            if leonardo_content_id in replacement_ids:
                leonardo_found = True
                logger.error(f"❌ Leonardo content found in replacement pair on iteration {i+1}")
                break
            
            logger.info(f"✅ Iteration {i+1}: Leonardo content not found in replacement pair")
        
        if not leonardo_found:
            logger.info("✅ Leonardo content was properly excluded from all replacement pairs")
        
        # Final summary
        logger.info("\n📋 Final Summary:")
        if not excluded_content_found and not passed_content_found and not any_excluded_found and not leonardo_found:
            logger.info("✅ PASS: All excluded content (not_interested, passed) was properly excluded from replacement pairs")
            return True
        else:
            logger.error("❌ FAIL: Some excluded content was found in replacement pairs")
            return False

    def test_voting_pair_with_excluded_content(self):
        """
        Test the regular voting-pair endpoint to verify that content marked as 
        "not_interested" or "passed" is properly excluded.
        """
        logger.info("\n🔍 TESTING REGULAR VOTING PAIR WITH EXCLUDED CONTENT")
        
        # Step 1: Register a new user if not already registered
        if not self.auth_token:
            logger.info("\n📋 Step 1: Register a new user")
            reg_success, reg_response = self.test_user_registration()
            if not reg_success:
                logger.error("❌ Failed to register user, stopping test")
                return False
        
        # Step 2: Get some initial voting pairs
        logger.info("\n📋 Step 2: Get initial voting pairs")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Step 3: Mark multiple content items as excluded
        logger.info("\n📋 Step 3: Mark multiple content items as excluded")
        excluded_items = []
        
        # Get 10 voting pairs and exclude one item from each
        for i in range(10):
            success, pair = self.test_get_voting_pair(use_auth=True)
            if not success:
                continue
            
            # Alternate between not_interested, passed, and watched
            interaction_type = ["not_interested", "passed", "watched"][i % 3]
            content_to_exclude = pair['item2']
            
            if interaction_type in ["not_interested", "watched"]:
                success, _ = self.test_content_interaction(
                    content_to_exclude['id'], 
                    interaction_type, 
                    use_auth=True
                )
            else:
                success, _ = self.test_pass_content(
                    content_to_exclude['id'], 
                    use_auth=True
                )
            
            if success:
                excluded_items.append({
                    "id": content_to_exclude['id'],
                    "title": content_to_exclude['title'],
                    "type": interaction_type
                })
                logger.info(f"Marked content as {interaction_type}: {content_to_exclude['title']} (ID: {content_to_exclude['id']})")
        
        logger.info(f"Excluded {len(excluded_items)} content items")
        
        # Step 4: Get multiple voting pairs and check for excluded content
        logger.info("\n📋 Step 4: Get multiple voting pairs and check for excluded content")
        
        excluded_found_count = 0
        total_pairs = 30
        
        for i in range(total_pairs):
            success, pair = self.test_get_voting_pair(use_auth=True)
            if not success:
                logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
                continue
            
            # Check if any excluded content appears in the pair
            pair_ids = [pair['item1']['id'], pair['item2']['id']]
            
            for excluded_item in excluded_items:
                if excluded_item['id'] in pair_ids:
                    excluded_found_count += 1
                    logger.error(f"❌ Excluded content '{excluded_item['title']}' ({excluded_item['type']}) found in voting pair on iteration {i+1}")
                    break
            
            if (i+1) % 5 == 0:
                logger.info(f"Progress: {i+1}/{total_pairs} pairs checked")
        
        exclusion_rate = 100 - (excluded_found_count / total_pairs * 100)
        logger.info(f"Exclusion rate: {exclusion_rate:.1f}% ({excluded_found_count} excluded items found in {total_pairs} pairs)")
        
        # Final summary
        logger.info("\n📋 Final Summary:")
        if excluded_found_count == 0:
            logger.info("✅ PASS: All excluded content was properly excluded from voting pairs")
            return True
        else:
            logger.error(f"❌ FAIL: Found {excluded_found_count} excluded content items in {total_pairs} voting pairs")
            return False

def test_voting_pair_replacement():
    """Main test function for voting pair replacement"""
    tester = VotingPairReplacementTester()
    
    # Run the comprehensive test for replacement endpoint
    replacement_result = tester.test_voting_pair_replacement_with_excluded_content()
    
    # Run the test for regular voting pair endpoint
    regular_result = tester.test_voting_pair_with_excluded_content()
    
    # Print summary
    logger.info("\n📊 TEST SUMMARY:")
    logger.info(f"Tests run: {tester.tests_run}")
    logger.info(f"Tests passed: {tester.tests_passed}")
    logger.info(f"Success rate: {tester.tests_passed/tester.tests_run*100:.1f}%")
    
    if replacement_result and regular_result:
        logger.info("✅ OVERALL RESULT: PASS - Both voting pair endpoints properly exclude content")
    elif replacement_result:
        logger.info("⚠️ PARTIAL PASS: Replacement endpoint works correctly, but regular voting pair has issues")
    elif regular_result:
        logger.info("⚠️ PARTIAL PASS: Regular voting pair works correctly, but replacement endpoint has issues")
    else:
        logger.error("❌ OVERALL RESULT: FAIL - Issues found with both voting pair endpoints")
    
    return replacement_result and regular_result

if __name__ == "__main__":
    test_voting_pair_replacement()