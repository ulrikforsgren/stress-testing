#!/usr/bin/env python3
"""
Test script for the JSONRPC client, specifically testing login functionality
and printing the session_id cookie.
"""

import asyncio
import sys
import pprint
from jsonrpc_api import JSONRPC


async def test_login():
    # Replace with your actual JSON-RPC server URL
    server_url = "http://localhost:8080/jsonrpc"
    
    # Replace with actual credentials
    username = "admin"
    password = "admin"
    
    print(f"Testing JSON-RPC login to {server_url}")
    
    try:
        # Initialize the JSON-RPC client
        async with JSONRPC(server_url, ssl=False, debug=True) as client:
            # Attempt to login
            print("===== LOGIN TEST =====")
            login_response = await client.login(username, password)
            
            if 'error' not in login_response:
                print(f"Login successful!")
                print(f"Auth token: {client.auth_token}")
                
                # Print all cookies from the session
                if client.client.session and client.client.session.cookie_jar:
                    print("\nCookies:")
                    for cookie in client.client.session.cookie_jar:
                        print(f"  {cookie.key}: {cookie.value}")
                        # Print specifically the session_id if it exists
                        if cookie.key == 'session_id':
                            print(f"\nSession ID: {cookie.value}")
                    print("===== GET TRANS =====")
                    print(await client.get_trans())
                    print("===== NEW TRANS =====")
                    th = await client.new_trans('read_write')
                    print(th)
                    print("===== GET SCHEMA =====")
                    schema_result = await client.get_schema(th, '/ncs:devices/global-settings/read-timeout', insert_values=True)
                    pprint.pprint(schema_result, width=80, compact=False)
                    print("===== GET VALUE =====")
                    print(await client.get_value(th, '/devices/global-settings/read-timeout'))
                    print("===== GET VALUE =====")
                    print(await client.get_value_as_type(th, '/python-service/service{S0}/str-value'))
                    print("===== GET VALUES =====")
                    print(await client.get_values(th, '/devices/global-settings', ['read-timeout', 'write-timeout']))
                    print("===== LOAD =====")
                    print(await client.load(th, '/ncs:devices/global-settings', {'read-timeout': 302, 'write-timeout': 302}))
                    print("===== APPLY =====")
                    print(await client.apply(th))
                # Test logout
                logout_response = await client.logout()
                if 'error' in logout_response:
                    print(f"Logout failed: {logout_response}")
                else:
                    print(f"Logout successful: {logout_response}")
            else:
                print("Login failed:", login_response)
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


def main():
    # Run the async test function
    try:
        asyncio.run(test_login())
        return 0
    except KeyboardInterrupt:
        print("Test interrupted.")
        return 1
    except Exception as e:
        print(f"Unhandled exception: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
