import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Test configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "default_api_key")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Sample test data based on the requirements
TEST_DATA = {
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
    "questions": [
        "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
        "What is the waiting period for pre-existing diseases (PED) to be covered?",
        "Does this policy cover maternity expenses, and what are the conditions?",
        "What is the waiting period for cataract surgery?",
        "Are the medical expenses for an organ donor covered under this policy?",
        "What is the No Claim Discount (NCD) offered in this policy?",
        "Is there a benefit for preventive health check-ups?",
        "How does the policy define a 'Hospital'?",
        "What is the extent of coverage for AYUSH treatments?",
        "Are there any sub-limits on room rent and ICU charges for Plan A?"
    ]
}

async def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            print(f"Health check status: {response.status_code}")
            print(f"Health check response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {str(e)}")
            return False

async def test_hackrx_endpoint():
    """Test the /hackrx/run endpoint"""
    print("\nTesting /hackrx/run endpoint...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Sending request to /hackrx/run...")
            print(f"Document URL: {TEST_DATA['documents']}")
            print(f"Number of questions: {len(TEST_DATA['questions'])}")
            
            response = await client.post(
                f"{API_BASE_URL}/hackrx/run",
                json=TEST_DATA,
                headers=headers
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Number of answers received: {len(result.get('answers', []))}")
                
                # Print questions and answers
                for i, (question, answer) in enumerate(zip(TEST_DATA['questions'], result.get('answers', []))):
                    print(f"\nQ{i+1}: {question}")
                    print(f"A{i+1}: {answer}")
                
                return True
            else:
                print(f"Error response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return False

async def test_authentication():
    """Test authentication with invalid token"""
    print("\nTesting authentication with invalid token...")
    
    headers = {
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/hackrx/run",
                json=TEST_DATA,
                headers=headers
            )
            
            print(f"Auth test status: {response.status_code}")
            expected_status = 401
            
            if response.status_code == expected_status:
                print("✓ Authentication working correctly")
                return True
            else:
                print(f"✗ Expected status {expected_status}, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Auth test failed: {str(e)}")
            return False

async def main():
    """Run all tests"""
    print("Starting API tests...")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...")
    
    # Test health endpoint
    health_ok = await test_health_endpoint()
    
    # Test authentication
    auth_ok = await test_authentication()
    
    # Test main endpoint
    main_ok = await test_hackrx_endpoint()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Health check: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Authentication: {'✓ PASS' if auth_ok else '✗ FAIL'}")
    print(f"Main endpoint: {'✓ PASS' if main_ok else '✗ FAIL'}")
    
    all_passed = health_ok and auth_ok and main_ok
    print(f"\nOverall result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())