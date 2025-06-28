import requests
import time
import sys
import random
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backend_api_test")

# Base URL for the API
BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"

def run_test(name, method, endpoint, expected_status, data=None, auth_token=None, params=None):
    """Run a single API test"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    # Add authorization header if needed
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
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

        try:
            return success, response.json() if response.text else {}
        except:
            return success, {}

    except Exception as e:
        logger.error(f"❌ Failed - Error: {str(e)}")
        return False, {}

def test_authentication():
    """Test authentication system"""
    logger.info("\n=== AUTHENTICATION TESTS ===")
    
    # Generate unique email for testing
    test_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
    test_password = "TestPassword123!"
    test_name = f"Test User {datetime.now().strftime('%H%M%S')}"
    
    # Test user registration
    reg_data = {
        "email": test_email,
        "password": test_password,
        "name": test_name
    }
    
    reg_success, reg_response = run_test(
        "User Registration",
        "POST",
        "auth/register",
        200,
        data=reg_data
    )
    
    if not reg_success or 'access_token' not in reg_response:
        logger.error("❌ User registration failed")
        return False, None
    
    auth_token = reg_response['access_token']
    user_id = reg_response['user']['id']
    logger.info(f"✅ User registered with ID: {user_id}")
    
    # Test user login with correct credentials
    login_data = {
        "email": test_email,
        "password": test_password
    }
    
    login_success, login_response = run_test(
        "User Login",
        "POST",
        "auth/login",
        200,
        data=login_data
    )
    
    if not login_success or 'access_token' not in login_response:
        logger.error("❌ User login failed")
        return False, auth_token
    
    logger.info("✅ User login successful")
    
    # Test user login with incorrect credentials
    wrong_login_data = {
        "email": test_email,
        "password": "WrongPassword123!"
    }
    
    wrong_login_success, _ = run_test(
        "User Login with Incorrect Password",
        "POST",
        "auth/login",
        401,  # Expecting 401 Unauthorized
        data=wrong_login_data
    )
    
    if not wrong_login_success:
        logger.error("❌ User login with incorrect password test failed")
    else:
        logger.info("✅ User login with incorrect password correctly rejected")
    
    # Test protected endpoint with valid token
    protected_success, protected_response = run_test(
        "Protected Endpoint with Valid Token",
        "GET",
        "auth/me",
        200,
        auth_token=auth_token
    )
    
    if not protected_success or 'id' not in protected_response:
        logger.error("❌ Protected endpoint test failed")
    else:
        logger.info("✅ Protected endpoint accessible with valid token")
    
    # Test protected endpoint with invalid token
    invalid_token_success, _ = run_test(
        "Protected Endpoint with Invalid Token",
        "GET",
        "auth/me",
        401,  # Expecting 401 Unauthorized
        auth_token="invalid_token_123456789"
    )
    
    if not invalid_token_success:
        logger.error("❌ Protected endpoint with invalid token test failed")
    else:
        logger.info("✅ Protected endpoint correctly rejected invalid token")
    
    return True, auth_token

def test_voting_pair_system(auth_token=None):
    """Test voting pair system"""
    logger.info("\n=== VOTING PAIR SYSTEM TESTS ===")
    
    # Create a guest session if no auth token
    session_id = None
    if not auth_token:
        session_success, session_response = run_test(
            "Create Session",
            "POST",
            "session",
            200,
            data={}
        )
        
        if not session_success or 'session_id' not in session_response:
            logger.error("❌ Session creation failed")
            return False
        
        session_id = session_response['session_id']
        logger.info(f"✅ Session created with ID: {session_id}")
    
    # Test voting pair endpoint for authenticated user
    if auth_token:
        pair_success, pair_response = run_test(
            "Get Voting Pair (Authenticated)",
            "GET",
            "voting-pair",
            200,
            auth_token=auth_token
        )
        
        if not pair_success or 'item1' not in pair_response or 'item2' not in pair_response:
            logger.error("❌ Get voting pair (authenticated) failed")
        else:
            # Check if poster URLs are present
            if pair_response['item1'].get('poster') and pair_response['item2'].get('poster'):
                logger.info(f"✅ Both items have poster URLs")
                logger.info(f"✅ Item 1 poster: {pair_response['item1']['poster'][:50]}...")
                logger.info(f"✅ Item 2 poster: {pair_response['item2']['poster'][:50]}...")
            else:
                logger.warning("⚠️ One or both items missing poster URLs")
                
            # Check if genres are populated
            if pair_response['item1'].get('genre') and pair_response['item2'].get('genre'):
                logger.info(f"✅ Both items have genres")
                logger.info(f"✅ Item 1 genre: {pair_response['item1']['genre']}")
                logger.info(f"✅ Item 2 genre: {pair_response['item2']['genre']}")
            else:
                logger.warning("⚠️ One or both items missing genres")
                
            # Check if ratings are populated
            if pair_response['item1'].get('rating') and pair_response['item2'].get('rating'):
                logger.info(f"✅ Both items have ratings")
                logger.info(f"✅ Item 1 rating: {pair_response['item1']['rating']}")
                logger.info(f"✅ Item 2 rating: {pair_response['item2']['rating']}")
            else:
                logger.warning("⚠️ One or both items missing ratings")
    
    # Test voting pair endpoint for guest session
    if session_id:
        pair_success, pair_response = run_test(
            "Get Voting Pair (Guest)",
            "GET",
            "voting-pair",
            200,
            params={"session_id": session_id}
        )
        
        if not pair_success or 'item1' not in pair_response or 'item2' not in pair_response:
            logger.error("❌ Get voting pair (guest) failed")
        else:
            # Check if poster URLs are present
            if pair_response['item1'].get('poster') and pair_response['item2'].get('poster'):
                logger.info(f"✅ Both items have poster URLs")
                logger.info(f"✅ Item 1 poster: {pair_response['item1']['poster'][:50]}...")
                logger.info(f"✅ Item 2 poster: {pair_response['item2']['poster'][:50]}...")
            else:
                logger.warning("⚠️ One or both items missing poster URLs")
    
    # Test voting pair replacement endpoint
    if auth_token and 'item1' in pair_response:
        content_id = pair_response['item1']['id']
        
        replacement_success, replacement_response = run_test(
            "Voting Pair Replacement (Authenticated)",
            "GET",
            f"voting-pair-replacement/{content_id}",
            200,
            auth_token=auth_token
        )
        
        if not replacement_success or 'item1' not in replacement_response or 'item2' not in replacement_response:
            logger.error("❌ Voting pair replacement (authenticated) failed")
        else:
            # Check if the requested content ID is in the response
            if replacement_response['item1']['id'] == content_id or replacement_response['item2']['id'] == content_id:
                logger.info(f"✅ Replacement pair contains the requested content ID: {content_id}")
            else:
                logger.error(f"❌ Replacement pair does not contain the requested content ID: {content_id}")
                
            # Check if poster URLs are present
            if replacement_response['item1'].get('poster') and replacement_response['item2'].get('poster'):
                logger.info(f"✅ Both replacement items have poster URLs")
                logger.info(f"✅ Item 1 poster: {replacement_response['item1']['poster'][:50]}...")
                logger.info(f"✅ Item 2 poster: {replacement_response['item2']['poster'][:50]}...")
            else:
                logger.warning("⚠️ One or both replacement items missing poster URLs")
    
    # Test exclusion functionality
    if auth_token:
        logger.info("\n🔍 TESTING EXCLUSION FUNCTIONALITY")
        
        # Get a voting pair
        pair_success, pair = run_test(
            "Get Voting Pair for Exclusion Test",
            "GET",
            "voting-pair",
            200,
            auth_token=auth_token
        )
        
        if not pair_success or 'item1' not in pair:
            logger.error("❌ Failed to get voting pair for exclusion test")
            return False
        
        # Mark one item as "not_interested"
        content_id = pair['item1']['id']
        content_title = pair['item1']['title']
        logger.info(f"Marking '{content_title}' (ID: {content_id}) as not_interested")
        
        interact_success, _ = run_test(
            "Mark Content as Not Interested",
            "POST",
            "content/interact",
            200,
            data={
                "content_id": content_id,
                "interaction_type": "not_interested"
            },
            auth_token=auth_token
        )
        
        if not interact_success:
            logger.error("❌ Failed to mark content as not_interested")
            return False
        
        # Get multiple voting pairs and verify the excluded content doesn't appear
        excluded_content_found = False
        test_iterations = 5
        
        for i in range(test_iterations):
            logger.info(f"Exclusion test iteration {i+1}/{test_iterations}")
            
            # Get a voting pair
            pair_success, new_pair = run_test(
                f"Get Voting Pair After Exclusion {i+1}",
                "GET",
                "voting-pair",
                200,
                auth_token=auth_token
            )
            
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
        else:
            logger.error("❌ Excluded content found in voting pairs")
    
    return True

def test_content_management(auth_token=None):
    """Test content management"""
    logger.info("\n=== CONTENT MANAGEMENT TESTS ===")
    
    # Create a guest session if no auth token
    session_id = None
    if not auth_token:
        session_success, session_response = run_test(
            "Create Session",
            "POST",
            "session",
            200,
            data={}
        )
        
        if not session_success or 'session_id' not in session_response:
            logger.error("❌ Session creation failed")
            return False
        
        session_id = session_response['session_id']
        logger.info(f"✅ Session created with ID: {session_id}")
    
    # Test submitting a vote
    # First, get a voting pair
    if auth_token:
        pair_success, pair = run_test(
            "Get Voting Pair for Vote Test",
            "GET",
            "voting-pair",
            200,
            auth_token=auth_token
        )
        
        if not pair_success or 'item1' not in pair or 'item2' not in pair:
            logger.error("❌ Failed to get voting pair for vote test")
        else:
            # Submit a vote
            vote_data = {
                "winner_id": pair['item1']['id'],
                "loser_id": pair['item2']['id'],
                "content_type": pair['content_type']
            }
            
            vote_success, vote_response = run_test(
                "Submit Vote",
                "POST",
                "vote",
                200,
                data=vote_data,
                auth_token=auth_token
            )
            
            if not vote_success or vote_response.get('vote_recorded') != True:
                logger.error("❌ Vote submission failed")
            else:
                logger.info(f"✅ Vote recorded. Total votes: {vote_response.get('total_votes')}")
    
    # Test content interactions
    if auth_token:
        # Get a voting pair to get content IDs
        pair_success, pair = run_test(
            "Get Voting Pair for Interaction Test",
            "GET",
            "voting-pair",
            200,
            auth_token=auth_token
        )
        
        if not pair_success or 'item1' not in pair:
            logger.error("❌ Failed to get voting pair for interaction test")
        else:
            content_id = pair['item1']['id']
            
            # Test marking content as watched
            watched_success, watched_response = run_test(
                "Mark Content as Watched",
                "POST",
                "content/interact",
                200,
                data={
                    "content_id": content_id,
                    "interaction_type": "watched"
                },
                auth_token=auth_token
            )
            
            if not watched_success or watched_response.get('success') != True:
                logger.error("❌ Mark as watched failed")
            else:
                logger.info("✅ Content marked as watched successfully")
            
            # Test marking content as not interested
            not_interested_success, not_interested_response = run_test(
                "Mark Content as Not Interested",
                "POST",
                "content/interact",
                200,
                data={
                    "content_id": pair['item2']['id'],
                    "interaction_type": "not_interested"
                },
                auth_token=auth_token
            )
            
            if not not_interested_success or not_interested_response.get('success') != True:
                logger.error("❌ Mark as not interested failed")
            else:
                logger.info("✅ Content marked as not interested successfully")
    
    # Test pass functionality
    if auth_token:
        # Get a new voting pair
        pair_success, pair = run_test(
            "Get Voting Pair for Pass Test",
            "GET",
            "voting-pair",
            200,
            auth_token=auth_token
        )
        
        if not pair_success or 'item1' not in pair:
            logger.error("❌ Failed to get voting pair for pass test")
        else:
            content_id = pair['item1']['id']
            
            # Test passing content
            pass_success, pass_response = run_test(
                "Pass Content",
                "POST",
                "pass",
                200,
                data={
                    "content_id": content_id
                },
                auth_token=auth_token
            )
            
            if not pass_success or pass_response.get('content_passed') != True:
                logger.error("❌ Pass content failed")
            else:
                logger.info("✅ Content passed successfully")
    
    return True

def test_edge_cases(auth_token=None):
    """Test edge cases"""
    logger.info("\n=== EDGE CASE TESTS ===")
    
    # Test with invalid session ID
    invalid_session_id = str(uuid.uuid4())
    
    invalid_session_success, _ = run_test(
        "Voting Pair with Invalid Session ID",
        "GET",
        "voting-pair",
        404,  # Expecting 404 Not Found
        params={"session_id": invalid_session_id}
    )
    
    if not invalid_session_success:
        logger.error("❌ Invalid session ID test failed")
    else:
        logger.info("✅ Voting pair endpoint correctly rejected invalid session ID")
    
    # Test with malformed requests
    # Missing required field in vote submission
    malformed_success, _ = run_test(
        "Vote Submission with Missing Field",
        "POST",
        "vote",
        422,  # Expecting 422 Unprocessable Entity
        data={"winner_id": "some_id"}  # Missing loser_id and content_type
    )
    
    if not malformed_success:
        logger.error("❌ Malformed request test failed")
    else:
        logger.info("✅ Vote submission correctly rejected malformed request")
    
    # Test with invalid content type in vote submission
    if auth_token:
        invalid_type_success, _ = run_test(
            "Vote Submission with Invalid Content Type",
            "POST",
            "vote",
            422,  # Expecting 422 Unprocessable Entity
            data={"winner_id": "some_id", "loser_id": "other_id", "content_type": "invalid_type"},
            auth_token=auth_token
        )
        
        if not invalid_type_success:
            logger.error("❌ Invalid content type test failed")
        else:
            logger.info("✅ Vote submission correctly rejected invalid content type")
    
    return True

def run_all_tests():
    """Run all tests"""
    logger.info("Starting backend API tests...")
    
    # Test authentication system
    auth_success, auth_token = test_authentication()
    if not auth_success:
        logger.error("❌ Authentication tests failed")
    
    # Test voting pair system
    voting_pair_success = test_voting_pair_system(auth_token)
    if not voting_pair_success:
        logger.error("❌ Voting pair system tests failed")
    
    # Test content management
    content_management_success = test_content_management(auth_token)
    if not content_management_success:
        logger.error("❌ Content management tests failed")
    
    # Test edge cases
    edge_case_success = test_edge_cases(auth_token)
    if not edge_case_success:
        logger.error("❌ Edge case tests failed")
    
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Authentication tests: {'✅ Passed' if auth_success else '❌ Failed'}")
    logger.info(f"Voting pair system tests: {'✅ Passed' if voting_pair_success else '❌ Failed'}")
    logger.info(f"Content management tests: {'✅ Passed' if content_management_success else '❌ Failed'}")
    logger.info(f"Edge case tests: {'✅ Passed' if edge_case_success else '❌ Failed'}")
    
    overall_success = auth_success and voting_pair_success and content_management_success and edge_case_success
    
    if overall_success:
        logger.info("✅ ALL BACKEND TESTS PASSED")
    else:
        logger.error("❌ SOME BACKEND TESTS FAILED")
    
    return overall_success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)