"""
Pytest configuration file containing shared fixtures.
"""

import pytest
from stress_testing.jsonrpc_api import JSONRPC

# Configuration parameters
SERVER_URL = "http://localhost:8080/jsonrpc"
USERNAME = "admin"
PASSWORD = "admin"

@pytest.fixture
async def jsonrpc_client():
    """Fixture that provides a configured and logged-in JSONRPC client"""
    # Initialize client with debug mode off and no compression
    client = JSONRPC(SERVER_URL, ssl=False, debug=False, no_compression=True)
    await client.__aenter__()
    
    # Login
    login_success = await client.login(USERNAME, PASSWORD)
    assert login_success == {}
    print(f"Login successful")
    
    # Print session cookies
    if client.client.session and client.client.session.cookie_jar:
        print("\nSession cookies:")
        for cookie in client.client.session.cookie_jar:
            print(f"  {cookie.key}: {cookie.value}")
    # Provide the client to the test
    yield client
    
    # Cleanup after the test is done
    await client.logout()
    await client.__aexit__(None, None, None)
