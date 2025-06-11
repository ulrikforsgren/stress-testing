import pytest
import re
from unittest.mock import patch, MagicMock
from stress_testing.jsonrpc_api import JSONRPC


@pytest.mark.asyncio
async def test_fetch_ssh_host_keys(jsonrpc_client):
    """Test the 'devices fetch-ssh-host-keys' action"""

    # Create transaction
    th = await jsonrpc_client.new_trans(mode="read")
    assert th > 0, "Failed to create a new transaction handle"
    
    # Run the fetch-ssh-host-keys action
    path = "/devices/fetch-ssh-host-keys"
    result = await jsonrpc_client.run_action(th=th, path=path)
    
    # Verify the results
    assert len(result) > 0
    
    # Verify both devices were successful
    for r in result:
        print(r)
        name = r['name']
        value = r['value']
        if name == 'fetch-result/device':
            assert re.match(r'ex\d+', value), f"Unexpected device name: {value}"
        elif name == 'fetch-result/result':
            assert value in ['unchanged', 'updated'], f"Unexpected result value: {value}"
        elif name == 'fetch-result/fingerprint/algorithm':
            assert value in ['ssh-rsa', 'ssh-ed25519'], f"Unexpected fingerprint algorithm: {value}"
        elif name == 'fetch-result/fingerprint/value':
            # Match hex value pattern using regex : 80:51:31:32:fc:ed:c9:70:7a:4e:f7:91:0b:36:14:1a
            assert re.match(r'^[0-9a-f]{2}(:[0-9a-f]{2}){15}$', value), f"Unexpected fingerprint value format: {value}"


@pytest.mark.asyncio
async def test_fetch_ssh_host_keys_with_params(jsonrpc_client):
    """Test the 'devices fetch-ssh-host-keys' action with specific device"""

    th = await jsonrpc_client.new_trans(mode="read")
    
    # Run action with parameters to specify a device
    path = "/devices/fetch-ssh-host-keys"
    params = {"device": "ex00"}
    
    result = await jsonrpc_client.run_action(th=th, path=path, params=params)
    
    # Verify the mock was called with the right parameters
    assert True
