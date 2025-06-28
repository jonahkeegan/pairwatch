import requests
import time
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# Base URL for the API
BASE_URL = "https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"

def test_voting_pair_replacement():
    """Test voting pair replacement endpoint with poster URLs"""
    logger.info("Testing voting pair replacement endpoint...")
    
    # Step 1: Create a session
    session_response = requests.post(f"{BASE_URL}/session")
    if session_response.status_code != 200:
        logger.error(f"Failed to create session: {session_response.status_code}")
        return False
    
    session_id = session_response.json()['session_id']
    logger.info(f"Created session with ID: {session_id}")
    
    # Step 2: Get a voting pair
    pair_response = requests.get(f"{BASE_URL}/voting-pair", params={"session_id": session_id})
    if pair_response.status_code != 200:
        logger.error(f"Failed to get voting pair: {pair_response.status_code}")
        return False
    
    pair_data = pair_response.json()
    if 'item1' not in pair_data or 'item2' not in pair_data:
        logger.error("Voting pair response missing items")
        return False
    
    # Check if poster URLs are present
    if pair_data['item1'].get('poster') and pair_data['item2'].get('poster'):
        logger.info(f"Both items have poster URLs")
        logger.info(f"Item 1 poster: {pair_data['item1']['poster'][:50]}...")
        logger.info(f"Item 2 poster: {pair_data['item2']['poster'][:50]}...")
    else:
        logger.warning("One or both items missing poster URLs")
    
    # Step 3: Test replacement endpoint
    content_id = pair_data['item1']['id']
    replacement_response = requests.get(f"{BASE_URL}/voting-pair-replacement/{content_id}", params={"session_id": session_id})
    if replacement_response.status_code != 200:
        logger.error(f"Failed to get replacement pair: {replacement_response.status_code}")
        return False
    
    replacement_data = replacement_response.json()
    if 'item1' not in replacement_data or 'item2' not in replacement_data:
        logger.error("Replacement pair response missing items")
        return False
    
    # Check if the requested content ID is in the response
    if replacement_data['item1']['id'] == content_id or replacement_data['item2']['id'] == content_id:
        logger.info(f"Replacement pair contains the requested content ID: {content_id}")
    else:
        logger.error(f"Replacement pair does not contain the requested content ID: {content_id}")
        return False
    
    # Check if poster URLs are present in replacement pair
    if replacement_data['item1'].get('poster') and replacement_data['item2'].get('poster'):
        logger.info(f"Both replacement items have poster URLs")
        logger.info(f"Item 1 poster: {replacement_data['item1']['poster'][:50]}...")
        logger.info(f"Item 2 poster: {replacement_data['item2']['poster'][:50]}...")
        return True
    else:
        logger.warning("One or both replacement items missing poster URLs")
        return False

def test_pass_functionality():
    """Test pass functionality"""
    logger.info("Testing pass functionality...")
    
    # Step 1: Create a session
    session_response = requests.post(f"{BASE_URL}/session")
    if session_response.status_code != 200:
        logger.error(f"Failed to create session: {session_response.status_code}")
        return False
    
    session_id = session_response.json()['session_id']
    logger.info(f"Created session with ID: {session_id}")
    
    # Step 2: Get a voting pair
    pair_response = requests.get(f"{BASE_URL}/voting-pair", params={"session_id": session_id})
    if pair_response.status_code != 200:
        logger.error(f"Failed to get voting pair: {pair_response.status_code}")
        return False
    
    pair_data = pair_response.json()
    if 'item1' not in pair_data:
        logger.error("Voting pair response missing items")
        return False
    
    content_id = pair_data['item1']['id']
    content_title = pair_data['item1']['title']
    logger.info(f"Marking '{content_title}' (ID: {content_id}) as passed")
    
    # Step 3: Mark content as passed
    pass_response = requests.post(
        f"{BASE_URL}/pass",
        json={"content_id": content_id, "session_id": session_id}
    )
    
    if pass_response.status_code != 200:
        logger.error(f"Failed to pass content: {pass_response.status_code}")
        return False
    
    pass_data = pass_response.json()
    if pass_data.get('content_passed') != True:
        logger.error("Pass response does not indicate content was passed")
        return False
    
    logger.info("Content passed successfully")
    
    # Step 4: Get multiple voting pairs and verify the passed content doesn't appear
    passed_content_found = False
    test_iterations = 5
    
    for i in range(test_iterations):
        logger.info(f"Test iteration {i+1}/{test_iterations}")
        
        new_pair_response = requests.get(f"{BASE_URL}/voting-pair", params={"session_id": session_id})
        if new_pair_response.status_code != 200:
            logger.error(f"Failed to get voting pair on iteration {i+1}: {new_pair_response.status_code}")
            continue
        
        new_pair_data = new_pair_response.json()
        if 'item1' not in new_pair_data or 'item2' not in new_pair_data:
            logger.error(f"Voting pair response missing items on iteration {i+1}")
            continue
        
        # Check if the passed content appears
        if new_pair_data['item1']['id'] == content_id or new_pair_data['item2']['id'] == content_id:
            logger.error(f"Passed content '{content_title}' (ID: {content_id}) found in voting pair!")
            passed_content_found = True
            break
        else:
            logger.info(f"Passed content not found in voting pair {i+1}")
    
    if not passed_content_found:
        logger.info(f"Passed content successfully excluded from {test_iterations} voting pairs")
        return True
    else:
        logger.error("Passed content found in voting pairs")
        return False

def test_authentication():
    """Test authentication system"""
    logger.info("Testing authentication system...")
    
    # Generate unique email for testing
    test_email = f"test_user_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    test_name = f"Test User {int(time.time())}"
    
    # Step 1: Register a new user
    reg_data = {
        "email": test_email,
        "password": test_password,
        "name": test_name
    }
    
    reg_response = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    if reg_response.status_code != 200:
        logger.error(f"Failed to register user: {reg_response.status_code}")
        return False, None
    
    reg_data = reg_response.json()
    if 'access_token' not in reg_data:
        logger.error("Registration response missing access token")
        return False, None
    
    auth_token = reg_data['access_token']
    user_id = reg_data['user']['id']
    logger.info(f"User registered with ID: {user_id}")
    
    # Step 2: Login with correct credentials
    login_data = {
        "email": test_email,
        "password": test_password
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if login_response.status_code != 200:
        logger.error(f"Failed to login: {login_response.status_code}")
        return False, auth_token
    
    login_data = login_response.json()
    if 'access_token' not in login_data:
        logger.error("Login response missing access token")
        return False, auth_token
    
    logger.info("User login successful")
    
    # Step 3: Test protected endpoint
    headers = {"Authorization": f"Bearer {auth_token}"}
    me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if me_response.status_code != 200:
        logger.error(f"Failed to access protected endpoint: {me_response.status_code}")
        return False, auth_token
    
    me_data = me_response.json()
    if me_data.get('id') != user_id:
        logger.error("Protected endpoint returned incorrect user ID")
        return False, auth_token
    
    logger.info("Protected endpoint accessible with valid token")
    return True, auth_token

def run_tests():
    """Run all tests"""
    logger.info("Starting backend API tests...")
    
    # Test voting pair replacement
    voting_pair_replacement_success = test_voting_pair_replacement()
    if voting_pair_replacement_success:
        logger.info("✅ Voting pair replacement test passed")
    else:
        logger.error("❌ Voting pair replacement test failed")
    
    # Test pass functionality
    pass_functionality_success = test_pass_functionality()
    if pass_functionality_success:
        logger.info("✅ Pass functionality test passed")
    else:
        logger.error("❌ Pass functionality test failed")
    
    # Test authentication
    auth_success, auth_token = test_authentication()
    if auth_success:
        logger.info("✅ Authentication test passed")
    else:
        logger.error("❌ Authentication test failed")
    
    # Summary
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Voting pair replacement: {'✅ Passed' if voting_pair_replacement_success else '❌ Failed'}")
    logger.info(f"Pass functionality: {'✅ Passed' if pass_functionality_success else '❌ Failed'}")
    logger.info(f"Authentication: {'✅ Passed' if auth_success else '❌ Failed'}")
    
    overall_success = voting_pair_replacement_success and pass_functionality_success and auth_success
    
    if overall_success:
        logger.info("✅ ALL BACKEND TESTS PASSED")
    else:
        logger.error("❌ SOME BACKEND TESTS FAILED")
    
    return overall_success

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)