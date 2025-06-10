#!/usr/bin/env python3
"""
Pytest framework for JSONRPC client that:
1. Logs in using JSON-RPC
2. Creates a read transaction
3. Reads the read-timeout value
4. Creates a write transaction
5. Adds 10 to the read-timeout value and writes it back
6. Commits the transaction
"""

import pytest
import sys
from stress_testing.jsonrpc_api import JSONRPC

# Configuration parameters
TIMEOUT_PATH = "/devices/global-settings/read-timeout"


@pytest.mark.asyncio
async def test_modify_read_timeout(jsonrpc_client):
    """Test reading and modifying the read-timeout value"""
    print("\n===== Starting Read-Timeout Modification Test =====")

    # Step 1: Create a read transaction
    print("\nCreating read transaction...")
    read_th = await jsonrpc_client.new_trans('read')
    print(f"Read transaction handle: {read_th}")
    
    # Step 2: Read the current read-timeout value
    print(f"\nReading current value from {TIMEOUT_PATH}...")
    current_timeout = await jsonrpc_client.get_value_as_type(read_th, TIMEOUT_PATH, as_type=int)
    print(f"Current read-timeout value: {current_timeout}")
    
    # Step 3: Create a write transaction
    print("\nCreating write transaction...")
    write_th = await jsonrpc_client.new_trans('read_write')
    print(f"Write transaction handle: {write_th}")
    
    # Step 4: Modify the read-timeout value (add 10)
    new_timeout = current_timeout + 10
    print(f"\nSetting new read-timeout value: {new_timeout}")
    
    # Format the data for loading
    data = {
        "read-timeout": new_timeout
    }
    
    # Load the new value
    await jsonrpc_client.load(write_th, '/devices/global-settings', data)
    
    # Step 5: Commit the changes
    print("\nCommitting changes...")
    commit_result = await jsonrpc_client.apply(write_th)
    print(f"Commit result: {commit_result}")
    
    # Step 6: Verify the change
    print("\nVerifying the change...")
    verify_th = await jsonrpc_client.new_trans('read')
    updated_timeout = await jsonrpc_client.get_value_as_type(verify_th, TIMEOUT_PATH, as_type=int)
    print(f"Updated read-timeout value: {updated_timeout}")
    
    # Verify the value was changed correctly
    assert updated_timeout == new_timeout, f"Expected timeout value {new_timeout}, but got {updated_timeout}"
    
    print("\n===== Read-Timeout Modification Test Completed Successfully =====")


@pytest.mark.asyncio
async def test_modify_show_config(jsonrpc_client):
    """Test reading and modifying the read-timeout value"""
    print("\n===== Starting Read-Timeout Modification Test =====")
    
    # Create a write transaction
    print("\nCreating write transaction...")
    write_th = await jsonrpc_client.new_trans('read')
    print(f"Write transaction handle: {write_th}")
    
    # Show config
    result = await jsonrpc_client.show_config(write_th, '/python-service/service')
    print("RESULT", result)
    
    # Delete transaction
    print("\nDeleting write transaction...")
    await jsonrpc_client.delete_trans(write_th)
    assert False
        
    print("\n===== Show Config Test Completed Successfully =====")
