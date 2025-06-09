import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional


class JSONRPC:
    """
    JSON-RPC client implementation using asyncio and aiohttp for HTTP transport.
    Based on Cisco NSO JSON-RPC API documentation.
    """
    
    def __init__(self, url: str, ssl_verify: bool = True):
        """
        Initialize the JSON-RPC client.
        
        Args:
            url: URL of the JSON-RPC server endpoint
            ssl_verify: Whether to verify SSL certificates
        """
        self.url = url
        self.ssl_verify = ssl_verify
        self.session = None
        self.auth_token = None
        self.request_id = 0  # Initialize request_id as integer
    
    async def __aenter__(self):
        """Context manager entry"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _call(self, method: str, params: Optional[Dict[str, Any]] = None, 
                   require_auth: bool = False) -> Dict[str, Any]:
        """
        Make a JSON-RPC call.
        
        Args:
            method: RPC method name
            params: Parameters to pass to the method
            require_auth: Whether this call requires authentication
            
        Returns:
            The result from the JSON-RPC server
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        # Use and increment the instance's request_id
        self.request_id += 1
        request_id = self.request_id
        
        # Prepare JSON-RPC request
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params:
            request_data["params"] = params
        
        # Add authentication token if required and available
        headers = {
            "Content-Type": "application/json"
        }
        
        if require_auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Make the HTTP request
        print("REQUEST:", request_data)
        async with self.session.post(
            self.url,
            json=request_data,
            headers=headers,
            ssl=None if self.ssl_verify else False
        ) as response:
            if response.status != 200:
                raise Exception(f"HTTP error: {response.status}, {await response.text()}")
            
            response_data = await response.json()
            print(f"RESPONSE: {response_data}")
            
            # Check for JSON-RPC error
            if "error" in response_data:
                error = response_data["error"]
                raise Exception(f"JSON-RPC error: {error.get('code')}, {error.get('message')}")
            
            # Verify response ID matches request ID
            if response_data.get("id") != request_id:
                raise Exception("Response ID doesn't match request ID")
            
            return response_data.get("result")
    
    async def login(self, username: str, password: str) -> bool:
        """
        Log in to the JSON-RPC server.
        
        Args:
            username: User name
            password: User password
            
        Returns:
            True if login was successful
        """
        params = {
            "user": username,
            "passwd": password
        }
        
        try:
            result = await self._call("login", params)
            return True
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
    async def logout(self) -> bool:
        """
        Log out from the JSON-RPC server, invalidating the current session.
        
        Returns:
            True if logout was successful
        """
        if not self.auth_token:
            return True  # Already logged out
        
        try:
            await self._call("logout", {})
            self.auth_token = None
            return True
        except Exception as e:
            print(f"Logout failed: {str(e)}")
            return False
    
    async def get_value(self, th: int, path: str) -> Any:
        """
        Get a single value from the specified path.
        
        Args:
            path: Path to the data element in the data model
            th: Transaction handle (integer)
            
        Returns:
            The value at the specified path
        """
        params = {
            "th": th,
            "path": path
        }
        
        try:
            return (await self._call("get_value", params))['value']
        except Exception as e:
            print(f"get_value failed for path {path}: {str(e)}")
            raise
    
    async def get_values(self, th: int, path: str, leafs: list) -> Dict[str, Any]:
        """
        Get multiple values from the specified paths.
        
        Args:
            paths: List of paths to the data elements in the data model
            th: Transaction handle (integer)
            
        Returns:
            Dictionary mapping paths to their values
        """
        params = {
            "th": th,
            "path": path,
            "leafs": leafs
        }
        
        try:
            return (await self._call("get_values", params))['values']
        except Exception as e:
            print(f"get_values failed: {str(e)}")
            raise
    
    async def get_attrs(self, th: int, path: str, names: list) -> Dict[str, Any]:
        """
        Get attributes for a node in the data model.
        
        Args:
            path: Path to the node in the data model
            attrs: Optional list of attribute names to retrieve. 
                  If None, all attributes are retrieved.
            th: Transaction handle (integer)
            
        Returns:
            Dictionary of attribute names and values
        """
        params = {
            "th": th,
            "path": path,
            "names": names
        }
     
        try:
            return (await self._call("get_attrs", params))['attrs']
        except Exception as e:
            print(f"get_attrs failed for path {path}: {str(e)}")
            raise
    
    async def get_trans(self) -> str:
        """
        Get the current transaction ID.
        
        Returns:
            The current transaction ID
        """
        try:
            return (await self._call("get_trans"))['trans']
        except Exception as e:
            print(f"get_trans failed: {str(e)}")
            raise
    
    async def new_trans(self, mode: str = "read_write") -> str:
        """
        Create a new transaction.
        
        Args:
            mode: Transaction mode, one of 'read', 'read_write', or 'private'
                 Default is 'read_write'
                 
        Returns:
            The transaction ID of the new transaction
        """
        params = {
            "mode": mode
        }
        
        try:
            result = await self._call("new_trans", params)
            return result['th']
        except Exception as e:
            print(f"new_trans failed: {str(e)}")
            raise
    
    async def load(self, th: int, path: str, data: str|dict, format: str = "json", mode: str = "merge") -> Dict[str, Any]:
        """
        Load configuration data into the specified path.
        
        Args:
            th: Transaction handle (integer)
            path: Target path in the data model
            data: The configuration data to load
            format: Data format ('json', 'xml', or 'cli')
            mode: Load mode, one of 'merge', 'replace', or 'delete'
            
        Returns:
            Result of the load operation
        """
        if isinstance(data, dict):
            data = json.dumps(data)
        params = {
            "th": th,
            "path": path,
            "data": data,
            "format": format,
            "mode": mode
        }
        
        try:
            return await self._call("load", params, require_auth=True)
        except Exception as e:
            print(f"load failed for path {path}: {str(e)}")
            raise
    
    async def commit(self, th: int, flags: Optional[list:str] = None) -> Dict[str, Any]:
        """
        Commit a transaction.
        
        Args:
            th: Transaction handle (integer)
            flags: Optional list of commit flags
                  Possible values: 'no-networking', 'dry-run', 'no-out-of-sync-check',
                  'no-revision-check', 'synchronize'
                  
        Returns:
            Result of the commit operation
        """
        params = {
            "th": th
        }
        
        if flags:
            params["flags"] = flags
        
        try:
            return await self._call("commit", params, require_auth=True)
        except Exception as e:
            print(f"commit failed: {str(e)}")
            raise
    
    async def apply(self, th: int, flags: Optional[list:str] = None) -> Dict[str, Any]:
        """
        Apply all changes in the transaction.
        
        Args:
            th: Transaction handle (integer)
            flags: Optional list of apply flags (similar to commit flags)
                  
        Returns:
            Result of the apply operation
        """
        params = {
            "th": th
        }
        
        if flags:
            params["flags"] = flags
        
        try:
            return await self._call("apply", params, require_auth=True)
        except Exception as e:
            print(f"apply failed: {str(e)}")
            raise
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None