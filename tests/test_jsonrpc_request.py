import pytest
import json

# Service path and data constants
SERVICE_PATH = "/python-service"
SERVICE_NAME = "S1"
SERVICE_PATH2 = "/python-service/service{S1}"

# Initial service data
SERVICE_DATA = {
    'service': [
        {
            'name': SERVICE_NAME,
            'num-vlan': 1,
            'template': ['vlans']
        }
    ]
}

# Updated service data 
UPDATED_SERVICE_DATA = {
    'num-vlan': 2,
}


@pytest.mark.asyncio
@pytest.mark.order(1)
@pytest.mark.dependency()
async def test_create_service(jsonrpc_client):
    """Test creating a new service"""
    # Create the service
    result = await jsonrpc_client.request(
        op='create',
        resource=SERVICE_PATH,
        data=SERVICE_DATA
    )
    assert result == {}, "Service creation failed, expected empty response"

@pytest.mark.asyncio
@pytest.mark.order(2)
async def test_read_service(jsonrpc_client):
    """Test reading a service"""
    # Read the service
    result = await jsonrpc_client.request(
        op='read',
        resource=SERVICE_PATH
    )
    
    assert result['data']['python-service:python-service'] == SERVICE_DATA, "Service read failed, expected service intent"
    

@pytest.mark.asyncio
@pytest.mark.order(3)
async def test_update_service(jsonrpc_client):
    """Test updating a service"""
    # Update the service
    result = await jsonrpc_client.request(
        op='update',
        resource=SERVICE_PATH2,
        data=UPDATED_SERVICE_DATA
    )
    

@pytest.mark.asyncio
@pytest.mark.order(4)
async def test_delete_service(jsonrpc_client):
    """Test deleting a service"""
    # Delete the service
    result = await jsonrpc_client.request(
        op='delete',
        resource=SERVICE_PATH
    )
    
    assert result == {}, "Service deletion failed"