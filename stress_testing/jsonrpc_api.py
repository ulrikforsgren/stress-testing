import json
import asyncio
from typing import Dict, Any, Optional, Union
import jsonrpc_async
from jsonrpc_base.jsonrpc import ProtocolError
import aiohttp


class JSONRPC:
    """
    JSON-RPC client implementation using jsonrpc_async library.
    Based on Cisco NSO JSON-RPC API documentation.
    """
    
    def __init__(self, url: str, ssl: bool = True, debug: bool = False, no_compression: bool = False):
        """
        Initialize the JSON-RPC client.
        
        Args:
            url: URL of the JSON-RPC server endpoint
            ssl: Whether to verify SSL certificates
            debug: Whether to print debug information about requests and responses
            no_compression: Whether to prevent compression of response data
        """
        self.url = url
        self.ssl = ssl
        self.debug = debug
        self.auth_token = None
        self.client = None
        
        self.headers = {}
        if no_compression:
            self.headers["Accept-Encoding"] = "identity"
    
    async def __aenter__(self):
        """Context manager entry"""
        if self.client is None:
            # Create a new aiohttp session
            session = aiohttp.ClientSession(headers=self.headers)
            
            # Create the JSON-RPC client with our session
            self.client = jsonrpc_async.Server(
                self.url, 
                session=session,
                ssl=self.ssl
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client and hasattr(self.client, 'session') and self.client.session:
            await self.client.session.close()
            self.client = None
    

    async def _call(self, method: str, params: Optional[dict]=None) -> Any:
        """
        Generic method to make JSON-RPC calls with consistent error handling.
        
        Args:
            method: The JSON-RPC method name to call
            params: Optional parameters for the method
            
        Returns:
            The result of the JSON-RPC call
            
        Raises:
            Exception: Any exception that occurred during the call
        """
        if self.client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        params = params or {}
        
        try:
            if self.debug:
                print(f"Calling {method} with params: {params}")
            
            # Get the method from the client
            client_method = getattr(self.client, method)
            
            # Call the method with the provided parameters
            result = await client_method(**params)
            
            if self.debug:
                print(f"Result from {method}: {result}")
                
            return result
        except Exception as e:
            if self.debug:
                print(f"Error calling {method}: {str(e)}")
            raise

    async def login(self, username: str, password: str) -> bool:
        """
        Log in to the JSON-RPC server.
        
        Args:
            username: User name
            password: User password
            
        Returns:
            True if login was successful
        """
        params = {"user": username, "passwd": password}
        return await self._call("login", params)

    async def logout(self) -> bool:
        """
        Log out from the JSON-RPC server, invalidating the current session.
        
        Returns:
            True if logout was successful
        """
        return await self._call("logout")
    
    async def get_value(self, th: int, path: str) -> Any:
        """
        Get a single value from the specified path.
        
        Args:
            path: Path to the data element in the data model
            th: Transaction handle (integer)
            
        Returns:
            The value at the specified path
        """
        params = {"th": th, "path": path}
        response = await self._call("get_value", params)
        return response['value']
    
    async def get_value_as_type(self, th: int, path: str, as_type: str = None) -> Any:
        """
        Get a single value from the specified path with type checking.
        Returns None if data is not found.
        
        Args:
            th: Transaction handle (integer)
            path: Path to the data element in the data model
            as_type: Cast function for the value (optional)
            
        Returns:
            The value at the specified path, or None if data not found
        """
        try:
            params = {"th": th, "path": path}
            response = await self._call("get_value", params)
            if response is None:
                return None
            if as_type is str:
                return response['value']
            else:
                # If as_type is not specified, return the raw value
                return as_type(response['value'])
        except ProtocolError as e:
            if e.args[0] == -32000 and e.args[1] == 'Data not found':
                return None
            raise
    
    async def get_values(self, th: int, path: str, leafs: list) -> Dict[str, Any]:
        """
        Get multiple values from the specified paths.
        
        Args:
            th: Transaction handle (integer)
            path: Path to the container element
            leafs: List of leaf names to retrieve
            
        Returns:
            Dictionary mapping paths to their values
        """
        params = {"th": th, "path": path, "leafs": leafs}
        response = await self._call("get_values", params)
        return response['values']
    
    async def delete(self, th: int, path: str) -> Dict[str, Any]:
        """
        Delete a node in the data model.
        
        Args:
            th: Transaction handle (integer)
        Returns:
            {} | {"warnings": <array of strings>}
        """
        params = {"th": th, "path": path}
        response = await self._call("delete", params)
        return response


    async def get_attrs(self, th: int, path: str, names: list) -> Dict[str, Any]:
        """
        Get attributes for a node in the data model.
        
        Args:
            th: Transaction handle (integer)
            path: Path to the node in the data model
            names: List of attribute names to retrieve
            
        Returns:
            Dictionary of attribute names and values
        """
        params = {"th": th, "path": path, "names": names}
        response = await self._call("get_attrs", params)
        return response['attrs']
    
    async def get_trans(self) -> str:
        """
        Get the current transaction ID.
        
        Returns:
            The current transaction ID
        """
        response = await self._call("get_trans")
        return response['trans']
    
    async def new_trans(self, mode: str = "read_write") -> str:
        """
        Create a new transaction.
        
        Args:
            mode: Transaction mode, one of 'read', 'read_write', or 'private'
                 Default is 'read_write'
                 
        Returns:
            The transaction ID of the new transaction
        """
        params = {"mode": mode}
        result = await self._call("new_trans", params)
        return result['th']

    async def commit(self, th: int, flags: Optional[list] = None) -> Dict[str, Any]:
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
        params = {"th": th}
        if flags is not None:
            params["flags"] = flags
        return await self._call("commit", params)
    
    async def apply(self, th: int, flags: Optional[list] = None) -> Dict[str, Any]:
        """
        Apply all changes in the transaction.
        
        Args:
            th: Transaction handle (integer)
            flags: Optional list of apply flags (similar to commit flags)
                  
        Returns:
            Result of the apply operation
        """
        params = {"th": th}
        if flags is not None:
            params["flags"] = flags
        return await self._call("apply", params)
    
    async def delete_trans(self, th: int) -> Dict[str, Any]:
        """
        Delete a transaction.
        
        Args:
            th: Transaction handle (integer) to delete
            
        Returns:
            Result of the delete_trans operation
        """
        params = {"th": th}
        return await self._call("delete_trans", params)

    async def load(self, th: int, path: str, data: Union[str, dict], format: str = "json", mode: str = "merge") -> Dict[str, Any]:
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
        params = {"th": th, "path": path, "data": data, "format": format, "mode": mode}
        return await self._call("load", params)
        
    async def show_config(self, th: int, path: str, format: str = "json", 
                          depth: int = -1, operational: bool = False) -> Dict[str, Any]:
        """
        Show the configuration at the specified path.
        
        Args:
            th: Transaction handle (integer)
            path: Path to the configuration element to show
            format: Output format ('json', 'xml', or 'cli')
            depth: Maximum depth to show (-1 for all levels)
            operational: Whether to include operational data
            
        Returns:
            The configuration at the specified path
        """
        params = {
            "th": th,
            "path": path,
            "format": format
        }
        
        if depth != -1:
            params["depth"] = depth
            
        if operational:
            params["operational"] = operational
            
        return await self._call("show_config", params)
    
    async def get_schema(self, th: int, path: Optional[str] = None, namespace: Optional[str] = None,
                       levels: int = -1, insert_values: bool = False, 
                       evaluate_when_entries: bool = False, stop_on_list: bool = True,
                       cdm_namespace: bool = False) -> Dict[str, Any]:
        """
        Get schema information for a specific path in the data model.

        Args:
            namespace: Optional namespace for the schema query
            path: Optional path to the schema node
            th: Transaction handle (integer)
            insert_values: Whether to insert values in the schema
            evaluate_when_entries: Whether to evaluate 'when' entries
            stop_on_list: Whether to stop schema traversal on list nodes
            cdm_namespace: Whether to use CDM namespace
            levels: Number of schema levels to retrieve (-1 for all levels)
            
        Returns:
            Schema information for the specified path
        """
        params = {
            "th": th,
            "levels": levels,
            "insert_values": insert_values,
            "evaluate_when_entries": evaluate_when_entries,
            "stop_on_list": stop_on_list,
            "cdm_namespace": cdm_namespace
        }
        
        if path:
            params["path"] = path
            
        if namespace:
            params["namespace"] = namespace
        
        return await self._call("get_schema", params)
    
    async def close(self):
        """Close the HTTP session"""
        if self.client and hasattr(self.client, 'session') and self.client.session:
            await self.client.session.close()
            self.client = None


    async def request(self, op, resource, data=None, jdata=None,
                      resource_type='data', params=None):
        if op =='create':
            pass
        elif op == 'read':
            pass
        elif op == 'update':
            pass
        elif op == 'delete':
            pass
        elif op == 'action':
            pass
    
    async def run_action(self, th: int, path: str, input_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run an action at the specified path.
        
        Args:
            th: Transaction handle (integer)
            path: Path to the action in the data model
            input_params: Optional input parameters for the action
            
        Returns:
            Result of the action operation, typically containing output parameters
        """
        params = {"th": th, "path": path}
        if input_params:
            params["params"] = input_params
            
        return await self._call("run_action", params)