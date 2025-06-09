#!/usr/bin/env python3
"""
Test script for the JSONRPC client, specifically testing login functionality
and printing the session_id cookie.
"""

import asyncio
import sys
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
        async with JSONRPC(server_url, ssl_verify=False) as client:
            # Attempt to login
            print("===== LOGIN TEST =====")
            login_success = await client.login(username, password)
            
            if login_success:
                print(f"Login successful!")
                print(f"Auth token: {client.auth_token}")
                
                # Print all cookies from the session
                if client.session and client.session.cookie_jar:
                    print("\nCookies:")
                    for cookie in client.session.cookie_jar:
                        print(f"  {cookie.key}: {cookie.value}")
                        # Print specifically the session_id if it exists
                        if cookie.key == 'session_id':
                            print(f"\nSession ID: {cookie.value}")
                    print("===== GET TRANS =====")
                    print(await client.get_trans())
                    print("===== NEW TRANS =====")
                    th = await client.new_trans('read')
                    print(th)
                    print("===== GET VALUE =====")
                    print(await client.get_value(th, '/devices/global-settings/read-timeout'))
                    print("===== GET VALUES =====")
                    print(await client.get_values(th, '/devices/global-settings', ['read-timeout', 'write-timeout']))
                    print("===== LOAD =====")
                    print(await client.load(th, '/ncs:devices/global-settings', {'read-timeout': 302, 'write-timeout': 302}))
                    print("===== APPLY =====")
                    print(await client.apply(th))
                # Test logout
                logout_success = await client.logout()
                print(f"Logout successful: {logout_success}")
            else:
                print("Login failed.")
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
