#!/usr/bin/env python3
"""
Comprehensive test for the new "Pass" functionality in pairwise comparison voting.
Tests that passed content is permanently excluded from future voting pairs.
"""

import requests
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
logger = logging.getLogger("pass_functionality_test")

class PassFunctionalityTester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        self.session_id = None
        
        # Test user credentials
        self.test_user_email = f"pass_test_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Pass Test User {datetime.now().strftime('%H%M%S')}"
        
        # MongoDB connection
        self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.mongo_client["movie_preferences_db"]
        
        logger.info(f"🔍 Testing Pass Functionality at: {self.base_url}")
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

    def test_create_session(self):
        """Test creating a guest session"""
        success, response = self.run_test(
            "Create Guest Session",
            "POST",
            "session",
            200
        )
        
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            logger.info(f"✅ Session created with ID: {self.session_id}")
            return True, response
        
        return False, response

    def test_get_voting_pair(self, use_auth=True):
        """Get a pair of items for voting"""
        params = {}
        
        if use_auth and self.auth_token:
            auth = True
        elif self.session_id:
            params = {"session_id": self.session_id}
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
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

    def test_pass_content(self, content_id, use_auth=True):
        """Test passing on content"""
        data = {"content_id": content_id}
        
        if use_auth and self.auth_token:
            auth = True
        elif self.session_id:
            data["session_id"] = self.session_id
            auth = False
        else:
            logger.error("❌ No session ID or auth token available")
            return False, {}
        
        success, response = self.run_test(
            f"Pass Content ({content_id[:8]}...)",
            "POST",
            "pass",
            200,
            data=data,
            auth=auth
        )
        
        return success, response

    def test_pass_api_endpoint(self):
        """Test the /api/pass endpoint functionality"""
        logger.info("\n🔍 Testing Pass API Endpoint...")
        
        # Test with authenticated user
        logger.info("Testing with authenticated user...")
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ Failed to register user")
            return False
        
        # Get a voting pair
        pair_success, pair_response = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        # Extract content ID from the pair
        content_id = pair_response.get('item1', {}).get('id')
        if not content_id:
            logger.error("❌ No content ID found in voting pair")
            return False
        
        # Test passing on the content
        pass_success, pass_response = self.test_pass_content(content_id, use_auth=True)
        if not pass_success:
            logger.error("❌ Failed to pass content for authenticated user")
            return False
        
        if pass_response.get('content_passed') != True:
            logger.error("❌ Pass response doesn't confirm content was passed")
            return False
        
        logger.info("✅ Pass endpoint works for authenticated users")
        
        # Test with guest session
        logger.info("Testing with guest session...")
        session_success, _ = self.test_create_session()
        if not session_success:
            logger.error("❌ Failed to create guest session")
            return False
        
        # Get a voting pair for guest
        pair_success, pair_response = self.test_get_voting_pair(use_auth=False)
        if not pair_success:
            logger.error("❌ Failed to get voting pair for guest")
            return False
        
        # Extract content ID from the pair
        content_id = pair_response.get('item1', {}).get('id')
        if not content_id:
            logger.error("❌ No content ID found in voting pair for guest")
            return False
        
        # Test passing on the content as guest
        pass_success, pass_response = self.test_pass_content(content_id, use_auth=False)
        if not pass_success:
            logger.error("❌ Failed to pass content for guest user")
            return False
        
        logger.info("✅ Pass endpoint works for guest sessions")
        return True

    def test_pass_exclusion_in_voting_pairs(self):
        """Test that passed content is excluded from future voting pairs"""
        logger.info("\n🔍 Testing Pass Exclusion in Voting Pairs...")
        
        # Use the already registered user
        if not self.auth_token:
            logger.error("❌ No authenticated user available")
            return False
        
        passed_content_ids = set()
        
        # Pass on several content items
        for i in range(5):
            # Get a voting pair
            pair_success, pair_response = self.test_get_voting_pair(use_auth=True)
            if not pair_success:
                logger.error(f"❌ Failed to get voting pair {i+1}")
                return False
            
            # Pass on the first item
            content_id = pair_response.get('item1', {}).get('id')
            content_title = pair_response.get('item1', {}).get('title', 'Unknown')
            
            if not content_id:
                logger.error(f"❌ No content ID found in voting pair {i+1}")
                return False
            
            pass_success, _ = self.test_pass_content(content_id, use_auth=True)
            if not pass_success:
                logger.error(f"❌ Failed to pass content {i+1}")
                return False
            
            passed_content_ids.add(content_id)
            logger.info(f"✅ Passed content {i+1}: {content_title} ({content_id[:8]}...)")
        
        # Now test that passed content doesn't appear in subsequent voting pairs
        logger.info("Testing that passed content doesn't reappear...")
        
        for attempt in range(20):  # Check many voting pairs
            pair_success, pair_response = self.test_get_voting_pair(use_auth=True)
            if not pair_success:
                continue
            
            item1_id = pair_response.get('item1', {}).get('id')
            item2_id = pair_response.get('item2', {}).get('id')
            
            if item1_id in passed_content_ids:
                logger.error(f"❌ Passed content reappeared in voting pair: {item1_id}")
                return False
            
            if item2_id in passed_content_ids:
                logger.error(f"❌ Passed content reappeared in voting pair: {item2_id}")
                return False
        
        logger.info("✅ Passed content successfully excluded from all subsequent voting pairs")
        return True

    def test_interaction_storage(self):
        """Test that pass interactions are properly stored in database"""
        logger.info("\n🔍 Testing Interaction Storage...")
        
        if not self.user_id:
            logger.error("❌ No user ID available")
            return False
        
        # Get current pass interactions count
        initial_count = self.db.user_interactions.count_documents({
            "user_id": self.user_id,
            "interaction_type": "passed"
        })
        
        # Get a voting pair and pass on it
        pair_success, pair_response = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        content_id = pair_response.get('item1', {}).get('id')
        if not content_id:
            logger.error("❌ No content ID found")
            return False
        
        pass_success, _ = self.test_pass_content(content_id, use_auth=True)
        if not pass_success:
            logger.error("❌ Failed to pass content")
            return False
        
        # Check that interaction was stored
        final_count = self.db.user_interactions.count_documents({
            "user_id": self.user_id,
            "interaction_type": "passed"
        })
        
        if final_count != initial_count + 1:
            logger.error(f"❌ Pass interaction not stored. Expected {initial_count + 1}, got {final_count}")
            return False
        
        # Verify the interaction details
        pass_interaction = self.db.user_interactions.find_one({
            "user_id": self.user_id,
            "content_id": content_id,
            "interaction_type": "passed"
        })
        
        if not pass_interaction:
            logger.error("❌ Pass interaction not found in database")
            return False
        
        logger.info(f"✅ Pass interaction properly stored: {pass_interaction['id']}")
        return True

    def test_edge_cases(self):
        """Test edge cases for pass functionality"""
        logger.info("\n🔍 Testing Edge Cases...")
        
        # Test passing the same content multiple times
        logger.info("Testing duplicate pass on same content...")
        pair_success, pair_response = self.test_get_voting_pair(use_auth=True)
        if not pair_success:
            logger.error("❌ Failed to get voting pair")
            return False
        
        content_id = pair_response.get('item1', {}).get('id')
        if not content_id:
            logger.error("❌ No content ID found")
            return False
        
        # Pass twice on the same content
        pass1_success, _ = self.test_pass_content(content_id, use_auth=True)
        pass2_success, _ = self.test_pass_content(content_id, use_auth=True)
        
        if not (pass1_success and pass2_success):
            logger.error("❌ Failed to pass same content multiple times")
            return False
        
        logger.info("✅ Duplicate pass on same content handled correctly")
        
        # Test with invalid content ID
        logger.info("Testing with invalid content ID...")
        invalid_success, invalid_response = self.test_pass_content("invalid-content-id", use_auth=True)
        
        # This should still succeed (the API doesn't validate content existence)
        if not invalid_success:
            logger.error("❌ Failed to handle invalid content ID")
            return False
        
        logger.info("✅ Invalid content ID handled correctly")
        
        # Test with missing content_id field
        logger.info("Testing with missing content_id field...")
        data = {}  # Missing content_id
        
        if self.auth_token:
            auth = True
        else:
            data["session_id"] = self.session_id
            auth = False
        
        missing_success, missing_response = self.run_test(
            "Pass with Missing Content ID",
            "POST",
            "pass",
            400,  # Should return 400 for missing field
            data=data,
            auth=auth
        )
        
        if not missing_success:
            logger.error("❌ Failed to handle missing content_id field correctly")
            return False
        
        logger.info("✅ Missing content_id field handled correctly")
        return True

    def run_all_tests(self):
        """Run all pass functionality tests"""
        logger.info("🚀 Starting Pass Functionality Tests...")
        
        test_results = {
            "pass_api_endpoint": False,
            "pass_exclusion": False,
            "interaction_storage": False,
            "edge_cases": False
        }
        
        try:
            # Test 1: Pass API Endpoint
            test_results["pass_api_endpoint"] = self.test_pass_api_endpoint()
            
            # Test 2: Pass Exclusion in Voting Pairs
            test_results["pass_exclusion"] = self.test_pass_exclusion_in_voting_pairs()
            
            # Test 3: Interaction Storage
            test_results["interaction_storage"] = self.test_interaction_storage()
            
            # Test 4: Edge Cases
            test_results["edge_cases"] = self.test_edge_cases()
            
        except Exception as e:
            logger.error(f"❌ Unexpected error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Print summary
        logger.info("\n📋 Pass Functionality Test Results:")
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        all_passed = all(test_results.values())
        overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
        logger.info(f"\n🎯 Overall Result: {overall_status}")
        
        return all_passed

def main():
    tester = PassFunctionalityTester()
    success = tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 Pass functionality is working correctly!")
        return 0
    else:
        logger.error("\n💥 Pass functionality has issues that need to be addressed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())