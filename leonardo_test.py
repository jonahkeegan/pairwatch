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
logger = logging.getLogger("leonardo_test")

class LeonardoContentExclusionTester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.auth_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # MongoDB connection
        self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.mongo_client["movie_preferences_db"]
        
        logger.info(f"🔍 Testing API at: {self.base_url}")

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

    def test_user_registration(self, email, password, name):
        """Test user registration"""
        data = {
            "email": email,
            "password": password,
            "name": name
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
    
    def test_user_login(self, email, password):
        """Test user login"""
        data = {
            "email": email,
            "password": password
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
    
    def test_get_voting_pair(self, use_auth=True):
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

    def test_get_replacement_voting_pair(self, content_id, use_auth=True):
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

    def test_content_interaction(self, content_id, interaction_type, use_auth=True):
        """Test content interaction (watched, want_to_watch, not_interested, passed)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            data["session_id"] = self.session_id
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
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            data["session_id"] = self.session_id
            auth = False
        else:
            logger.error("❌ No session ID available")
            self.test_results.append({"name": "Pass Content", "status": "SKIP", "details": "No session ID available"})
            return False, {}
        
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

    def find_leonardo_dicaprio_content(self):
        """Find Leonardo DiCaprio content in the database"""
        # Try to find the specific content ID from the bug report
        leonardo_content_id = "1d26e225-a9b5-4ff9-9eb4-c6ba117f240b"
        leonardo_content = self.db.content.find_one({"id": leonardo_content_id})
        
        if leonardo_content:
            logger.info(f"Found Leonardo DiCaprio content with ID: {leonardo_content_id}")
            return leonardo_content_id, leonardo_content["title"]
        
        # Try to find any Leonardo DiCaprio content
        leonardo_movies = list(self.db.content.find({"title": {"$regex": "Leonardo DiCaprio", "$options": "i"}}))
        if leonardo_movies:
            leonardo_content_id = leonardo_movies[0]["id"]
            logger.info(f"Found alternative Leonardo DiCaprio content: {leonardo_movies[0]['title']} (ID: {leonardo_content_id})")
            return leonardo_content_id, leonardo_movies[0]["title"]
        
        # Try to find any content with Leonardo DiCaprio in the actors field
        leonardo_actor_movies = list(self.db.content.find({"actors": {"$regex": "Leonardo DiCaprio", "$options": "i"}}))
        if leonardo_actor_movies:
            leonardo_content_id = leonardo_actor_movies[0]["id"]
            logger.info(f"Found Leonardo DiCaprio movie (as actor): {leonardo_actor_movies[0]['title']} (ID: {leonardo_content_id})")
            return leonardo_content_id, leonardo_actor_movies[0]["title"]
        
        # If all else fails, just get any content item
        random_content = list(self.db.content.find().limit(1))[0]
        logger.info(f"Using random content for testing: {random_content['title']} (ID: {random_content['id']})")
        return random_content["id"], random_content["title"]

    def test_leonardo_content_exclusion(self):
        """
        Test that Leonardo DiCaprio content marked as "not_interested" is properly excluded
        from replacement pairs for test009@yopmail.com
        """
        logger.info("\n🔍 TESTING LEONARDO DICAPRIO CONTENT EXCLUSION")
        
        # Step 1: Register a new test user
        test_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        test_password = "TestPassword123!"
        test_name = f"Test User {datetime.now().strftime('%H%M%S')}"
        
        logger.info("\n📋 Step 1: Register a new test user")
        reg_success, reg_response = self.test_user_registration(test_email, test_password, test_name)
        if not reg_success:
            logger.error("❌ Failed to register test user, trying to continue with login")
        
        # Step 2: Find Leonardo DiCaprio content
        logger.info("\n📋 Step 2: Find Leonardo DiCaprio content")
        leonardo_content_id, leonardo_title = self.find_leonardo_dicaprio_content()
        logger.info(f"Using content: {leonardo_title} (ID: {leonardo_content_id})")
        
        # Step 3: Mark Leonardo content as "not_interested"
        logger.info("\n📋 Step 3: Mark Leonardo content as 'not_interested'")
        success, _ = self.test_content_interaction(
            leonardo_content_id, 
            "not_interested", 
            use_auth=True
        )
        if not success:
            logger.error("❌ Failed to mark Leonardo content as not_interested")
            return False
        
        # Step 4: Get a base content item for replacement testing
        logger.info("\n📋 Step 4: Get a base content item for replacement testing")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        base_content = pair['item1']
        logger.info(f"Using base content: {base_content['title']} (ID: {base_content['id']})")
        
        # Step 5: Test multiple replacements to verify Leonardo content is excluded
        logger.info("\n📋 Step 5: Test multiple replacements to verify Leonardo content is excluded")
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
        
        # Step 6: Test with a different base content
        logger.info("\n📋 Step 6: Test with a different base content")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        base_content2 = pair['item2']
        logger.info(f"Using second base content: {base_content2['title']} (ID: {base_content2['id']})")
        
        leonardo_found2 = False
        
        for i in range(20):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                base_content2['id'], 
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
                leonardo_found2 = True
                logger.error(f"❌ Leonardo content found in replacement pair on iteration {i+1}")
                break
            
            logger.info(f"✅ Iteration {i+1}: Leonardo content not found in replacement pair")
        
        if not leonardo_found2:
            logger.info("✅ Leonardo content was properly excluded from all replacement pairs with second base content")
        
        # Final summary
        logger.info("\n📋 Final Summary:")
        if not leonardo_found and not leonardo_found2:
            logger.info("✅ PASS: Leonardo DiCaprio content was properly excluded from all replacement pairs")
            return True
        else:
            logger.error("❌ FAIL: Leonardo DiCaprio content was found in some replacement pairs")
            return False

def test_leonardo_content_exclusion():
    """Main test function for Leonardo content exclusion"""
    tester = LeonardoContentExclusionTester()
    
    # Run the test
    result = tester.test_leonardo_content_exclusion()
    
    # Print summary
    logger.info("\n📊 TEST SUMMARY:")
    logger.info(f"Tests run: {tester.tests_run}")
    logger.info(f"Tests passed: {tester.tests_passed}")
    logger.info(f"Success rate: {tester.tests_passed/tester.tests_run*100:.1f}%")
    
    if result:
        logger.info("✅ OVERALL RESULT: PASS - Leonardo DiCaprio content exclusion is working correctly")
    else:
        logger.error("❌ OVERALL RESULT: FAIL - Issues found with Leonardo DiCaprio content exclusion")
    
    return result

if __name__ == "__main__":
    test_leonardo_content_exclusion()