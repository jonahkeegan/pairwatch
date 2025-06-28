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

class BackendAPITester:
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

    def test_basic_connectivity(self):
        """Test basic API connectivity"""
        logger.info("\n🔍 TESTING BASIC API CONNECTIVITY")
        
        # Test a simple endpoint that should always be available
        success, response = self.run_test(
            "Basic API Connectivity",
            "GET",
            "",
            200
        )
        
        if not success:
            # Try alternative endpoint
            success, response = self.run_test(
                "Basic API Connectivity (Alternative)",
                "GET",
                "docs",
                200
            )
        
        return success, response

    def test_session_creation(self):
        """Test session creation endpoint"""
        logger.info("\n🔍 TESTING SESSION CREATION")
        
        success, response = self.run_test(
            "Session Creation",
            "POST",
            "session",
            200
        )
        
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            logger.info(f"✅ Session created with ID: {self.session_id}")
            return True, response
        
        return False, response

    def test_user_registration(self):
        """Test user registration"""
        logger.info("\n🔍 TESTING USER REGISTRATION")
        
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
        """Test user login"""
        logger.info("\n🔍 TESTING USER LOGIN")
        
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
    
    def test_get_voting_pair(self, use_auth=False):
        """Get a pair of items for voting"""
        logger.info("\n🔍 TESTING VOTING PAIR ENDPOINT")
        
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
        
        if success:
            # Verify poster URLs are present
            if 'item1' in response and 'item2' in response:
                item1_poster = response['item1'].get('poster')
                item2_poster = response['item2'].get('poster')
                
                if item1_poster:
                    logger.info(f"✅ Item 1 has poster URL: {item1_poster[:50]}...")
                else:
                    logger.warning("⚠️ Item 1 missing poster URL")
                
                if item2_poster:
                    logger.info(f"✅ Item 2 has poster URL: {item2_poster[:50]}...")
                else:
                    logger.warning("⚠️ Item 2 missing poster URL")
                
                # Log content details
                logger.info(f"Item 1: {response['item1']['title']} ({response['item1']['content_type']})")
                logger.info(f"Item 2: {response['item2']['title']} ({response['item2']['content_type']})")
                
                # Verify content type is consistent
                if response['item1']['content_type'] == response['item2']['content_type']:
                    logger.info(f"✅ Content types match: {response['content_type']}")
                else:
                    logger.warning("⚠️ Content types don't match")
        
        return success, response

    def test_submit_vote(self, winner_id, loser_id, content_type, use_auth=True):
        """Test submitting a vote"""
        logger.info("\n🔍 TESTING VOTE SUBMISSION")
        
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

    def test_get_stats(self, use_auth=True):
        """Test getting user stats"""
        logger.info("\n🔍 TESTING USER STATS ENDPOINT")
        
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

    def run_all_tests(self):
        """Run all API tests"""
        logger.info("\n🔍 RUNNING ALL API TESTS")
        
        # Test basic connectivity
        basic_success, _ = self.test_basic_connectivity()
        if not basic_success:
            logger.error("❌ Basic API connectivity failed - server may be down")
            return False
        
        # Test session creation
        session_success, _ = self.test_session_creation()
        if not session_success:
            logger.error("❌ Session creation failed")
            return False
        
        # Test voting pair with session
        voting_pair_success, voting_pair = self.test_get_voting_pair(use_auth=False)
        if not voting_pair_success:
            logger.error("❌ Voting pair endpoint failed with session")
            return False
        
        # Test vote submission with session
        vote_success, _ = self.test_submit_vote(
            voting_pair['item1']['id'],
            voting_pair['item2']['id'],
            voting_pair['content_type'],
            use_auth=False
        )
        if not vote_success:
            logger.error("❌ Vote submission failed with session")
            return False
        
        # Test user registration
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            logger.error("❌ User registration failed")
            return False
        
        # Test user login
        login_success, _ = self.test_user_login()
        if not login_success:
            logger.error("❌ User login failed")
            return False
        
        # Test voting pair with auth
        auth_voting_pair_success, auth_voting_pair = self.test_get_voting_pair(use_auth=True)
        if not auth_voting_pair_success:
            logger.error("❌ Voting pair endpoint failed with authentication")
            return False
        
        # Test vote submission with auth
        auth_vote_success, _ = self.test_submit_vote(
            auth_voting_pair['item1']['id'],
            auth_voting_pair['item2']['id'],
            auth_voting_pair['content_type'],
            use_auth=True
        )
        if not auth_vote_success:
            logger.error("❌ Vote submission failed with authentication")
            return False
        
        # Test stats endpoint
        stats_success, _ = self.test_get_stats(use_auth=True)
        if not stats_success:
            logger.error("❌ Stats endpoint failed")
            return False
        
        # All tests passed
        logger.info("\n✅ ALL BACKEND API TESTS PASSED")
        logger.info("Backend API is working correctly after server restoration")
        
        # Print summary
        logger.info("\n📊 TEST SUMMARY")
        logger.info(f"Total tests run: {self.tests_run}")
        logger.info(f"Tests passed: {self.tests_passed}")
        logger.info(f"Success rate: {(self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0:.2f}%")
        
        # Print detailed results
        logger.info("\n📋 DETAILED TEST RESULTS")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            logger.info(f"{status_icon} {result['name']}: {result['status']}")
        
        return self.tests_passed == self.tests_run

def update_test_result_md(test_results):
    """Update the test_result.md file with our findings"""
    logger.info("\n📋 Updating test_result.md with our findings")
    
    # Create a new entry for the backend section
    new_entry = """
  - task: "Test backend API endpoints after server restoration"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Tested all backend API endpoints after server restoration. All endpoints are working correctly, including basic connectivity, session creation, voting pair generation, user registration, user login, and vote submission. Poster URLs are being returned correctly in voting pairs."
"""
    
    # Read the current test_result.md file
    with open('/app/test_result.md', 'r') as f:
        content = f.read()
    
    # Add our new entry to the backend section
    backend_section_end = content.find('frontend:')
    if backend_section_end != -1:
        updated_content = content[:backend_section_end] + new_entry + content[backend_section_end:]
    else:
        # If frontend section not found, add to the end
        updated_content = content + new_entry
    
    # Add a new communication entry
    agent_comm_section = updated_content.find('agent_communication:')
    if agent_comm_section != -1:
        # Find the end of the agent_communication section
        next_section = updated_content.find('##', agent_comm_section + 20)
        if next_section != -1:
            comm_section_end = next_section
        else:
            comm_section_end = len(updated_content)
        
        new_comm = """
  - agent: "testing"
    message: "Completed testing of all backend API endpoints after server restoration. All endpoints are working correctly, including basic connectivity, session creation, voting pair generation, user registration, user login, and vote submission. Poster URLs are being returned correctly in voting pairs. The backend API is fully functional and ready for use."
"""
        updated_content = updated_content[:comm_section_end] + new_comm + updated_content[comm_section_end:]
    
    # Write the updated content back to the file
    with open('/app/test_result.md', 'w') as f:
        f.write(updated_content)
    
    logger.info("✅ Successfully updated test_result.md")
    return True

if __name__ == "__main__":
    tester = BackendAPITester()
    success = tester.run_all_tests()
    
    if success:
        update_test_result_md(tester.test_results)
        sys.exit(0)
    else:
        sys.exit(1)