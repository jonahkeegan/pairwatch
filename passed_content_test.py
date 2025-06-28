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
logger = logging.getLogger("passed_content_test")

class PassedContentExclusionTester:
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

    def test_passed_content_exclusion(self):
        """
        Test that content marked as "passed" is properly excluded from replacement pairs
        """
        logger.info("\n🔍 TESTING PASSED CONTENT EXCLUSION")
        
        # Step 1: Register a new user
        logger.info("\n📋 Step 1: Register a new user")
        reg_success, reg_response = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user, stopping test")
            return False
        
        # Step 2: Get some initial voting pairs to find content to pass
        logger.info("\n📋 Step 2: Get initial voting pairs to find content to pass")
        passed_content_items = []
        
        # Get 5 voting pairs and pass on one item from each
        for i in range(5):
            success, pair = self.test_get_voting_pair(use_auth=True)
            if not success:
                logger.error(f"❌ Failed to get voting pair {i+1}")
                continue
            
            content_to_pass = pair['item2']
            logger.info(f"Content to pass {i+1}: {content_to_pass['title']} (ID: {content_to_pass['id']})")
            
            # Pass on the content
            success, _ = self.test_pass_content(content_to_pass['id'], use_auth=True)
            if not success:
                logger.error(f"❌ Failed to pass on content {i+1}")
                continue
            
            passed_content_items.append({
                "id": content_to_pass['id'],
                "title": content_to_pass['title']
            })
        
        if not passed_content_items:
            logger.error("❌ Failed to pass on any content, stopping test")
            return False
        
        logger.info(f"Successfully passed on {len(passed_content_items)} content items")
        
        # Step 3: Get a base content item for replacement testing
        logger.info("\n📋 Step 3: Get a base content item for replacement testing")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        base_content = pair['item1']
        logger.info(f"Using base content: {base_content['title']} (ID: {base_content['id']})")
        
        # Step 4: Test multiple replacements to verify passed content is excluded
        logger.info("\n📋 Step 4: Test multiple replacements to verify passed content is excluded")
        passed_content_found = False
        
        for i in range(20):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                base_content['id'], 
                use_auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if any passed content appears in the replacement pair
            replacement_ids = [
                replacement_pair['item1']['id'],
                replacement_pair['item2']['id']
            ]
            
            for passed_item in passed_content_items:
                if passed_item['id'] in replacement_ids:
                    passed_content_found = True
                    logger.error(f"❌ Passed content '{passed_item['title']}' found in replacement pair on iteration {i+1}")
                    break
            
            if passed_content_found:
                break
            
            logger.info(f"✅ Iteration {i+1}: No passed content found in replacement pair")
        
        if not passed_content_found:
            logger.info("✅ All passed content was properly excluded from replacement pairs")
        
        # Step 5: Test with a different base content
        logger.info("\n📋 Step 5: Test with a different base content")
        success, pair = self.test_get_voting_pair(use_auth=True)
        if not success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        base_content2 = pair['item2']
        logger.info(f"Using second base content: {base_content2['title']} (ID: {base_content2['id']})")
        
        passed_content_found2 = False
        
        for i in range(20):
            success, replacement_pair = self.test_get_replacement_voting_pair(
                base_content2['id'], 
                use_auth=True
            )
            
            if not success:
                logger.error(f"❌ Failed to get replacement pair on iteration {i+1}")
                continue
            
            # Check if any passed content appears in the replacement pair
            replacement_ids = [
                replacement_pair['item1']['id'],
                replacement_pair['item2']['id']
            ]
            
            for passed_item in passed_content_items:
                if passed_item['id'] in replacement_ids:
                    passed_content_found2 = True
                    logger.error(f"❌ Passed content '{passed_item['title']}' found in replacement pair on iteration {i+1}")
                    break
            
            if passed_content_found2:
                break
            
            logger.info(f"✅ Iteration {i+1}: No passed content found in replacement pair")
        
        if not passed_content_found2:
            logger.info("✅ All passed content was properly excluded from replacement pairs with second base content")
        
        # Final summary
        logger.info("\n📋 Final Summary:")
        if not passed_content_found and not passed_content_found2:
            logger.info("✅ PASS: All passed content was properly excluded from replacement pairs")
            return True
        else:
            logger.error("❌ FAIL: Some passed content was found in replacement pairs")
            return False

def test_passed_content_exclusion():
    """Main test function for passed content exclusion"""
    tester = PassedContentExclusionTester()
    
    # Run the test
    result = tester.test_passed_content_exclusion()
    
    # Print summary
    logger.info("\n📊 TEST SUMMARY:")
    logger.info(f"Tests run: {tester.tests_run}")
    logger.info(f"Tests passed: {tester.tests_passed}")
    logger.info(f"Success rate: {tester.tests_passed/tester.tests_run*100:.1f}%")
    
    if result:
        logger.info("✅ OVERALL RESULT: PASS - Passed content exclusion is working correctly")
    else:
        logger.error("❌ OVERALL RESULT: FAIL - Issues found with passed content exclusion")
    
    return result

if __name__ == "__main__":
    test_passed_content_exclusion()