# -*- mode: python; python-indent: 4 -*-

import asyncio
from base64 import b64encode
import json
import aiohttp
from yarl import URL
import sys
import logging

logger = logging.getLogger(__name__)

HEADERS_JSON = {
    'Accept': 'application/yang-data+json',
    'Accept-Encoding': 'identity',  # Prevent NSO from gzipping the data
    'Content-type': 'application/yang-data+json'
}

HEADERS_STREAM = {
    'Accept': 'text/event-stream',
    'Accept-Encoding': 'identity',  # Prevent NSO from gzipping data and delaying
    # sending of events.
}


def add_authentication(h, user, password):
    credentials = f'{user}:{password}'.encode('ascii')
    h['Authorization'] = 'Basic %s' % b64encode(credentials).decode("ascii")


# Expected response status for successful requests.
REQ_DISPATCH = {
    'create': ('POST', [201]),
    'read':   ('GET', [200]),
    'update': ('PATCH', [200, 204]),
    'set': ('PUT', [204]),
    'delete': ('DELETE', [200, 204]),
    'action': ('POST', [200, 204])
}


# This method is an extension of TCPConnector to setup an number of connections
# prior to doing requests

async def setup_pool_connections(self, conn, host, n_p):
    req = aiohttp.ClientRequest('GET', URL(f'http://{host}'))
    timeout = aiohttp.ClientTimeout(total=5 * 60)
    key = req.connection_key
    assert self._get(
        key) is None, "No connections should be setup at this time."
    connections = []
    for _ in range(0, n_p):
        proto = await self._create_connection(req, [], timeout)
        connections.append((proto, self._loop.time()))
    conn._conns[key] = connections


async def setup(task_args):
    aiohttp.TCPConnector.setup_pool_connections = setup_pool_connections
    conn = aiohttp.TCPConnector(limit=0)  # No limit of parallel connections
    client = aiohttp.ClientSession(connector=conn)
    task_args['client'] = client


async def teardown(task_args):
    await task_args['client'].close()


def get_client():
    conn = aiohttp.TCPConnector(limit=0)  # No limit of parallel connections
    timeout = aiohttp.ClientTimeout(total=None)  # No timeout
    client = aiohttp.ClientSession(connector=conn, timeout=timeout)
    return client


request_id = 0


async def restconf_request(args, client, host, op, resource, data=None,
                           resource_type='data', query_parameters=None):
    global request_id
    request_id += 1
    rid = request_id
    method, expected_status = REQ_DISPATCH[op]
    url = f'http://{host}/restconf/{resource_type}{resource}'
    if args.echo:
        logger.debug(f'{rid}: {method} {url}')
        if data: logger.debug(f'{rid}: {data}')
    if not args.dry_run:
        try:
            if data is not None:
                data = data.encode('utf-8')
            headers = HEADERS_JSON.copy()
            add_authentication(headers, 'admin', 'admin')
            async with client.request(method, url, headers=headers,
                                    data=data, params=query_parameters) as response:
                if response.status in [201, 204]:
                    data = None  # No content is expected.
                else:
                    if response.headers['Content-Type'] == 'application/yang-data+json':
                        data = await response.json()
                    else:
                        data = await response.text()
                res = 'ok' if response.status in expected_status else 'nok'
                return (rid, res, response.status, data)
        except Exception as e:
            return (rid, 'exception', None, repr(e))
    else:
        return (rid, 'ok', 418, 'dry-run') # I'm a teapot (RFC 2324, means no request is sent)


class RESTCONF:
    def __init__(self, host, user, password, client=None, log=None):
        if client is not None:
            self.client = client
        else:
            self.client = get_client()
        self.host = host
        self.user = user
        self.password = password
        self.headers = HEADERS_JSON.copy()
        add_authentication(self.headers, self.user, self.password)
        self.idval = 0
        self.idlock = asyncio.Lock()
        if log is not None:
            self.log = log
        else:
            self.log = lambda *msg: None

    async def next_id(self):
        async with self.idlock:
            self.idval += 1
            return self.idval

    # TODO: Handle token to speed up authentication
    # Returns tuples:
    # Successful: (request-id, "ok"/"nok", http-status, data/json)
    # Exception:  (request-id, "exception", exception-object)
    #

    async def request(self, op, resource, data=None, jdata=None,
                      resource_type='data', params=None):
        method, expected_status = REQ_DISPATCH[op]
        url = f'http://{self.host}/restconf/{resource_type}{resource}'
        if params is not None:
            # aiohttp request uses yarl.URL is used for params and can not handle
            # params without equal sign (=). Putting them directly in the url instead.
            url += '?' + params
        # yarl.URL unencodes %27 to ' preventing with encode=True
        url = URL(url, encoded=True)
        try:
            rid = await self.next_id()
            if data is not None:
                await self.log(self.host, 'restconf', 'request', rid=rid,
                               method=method, url=url, data=data)
                data = data.encode('utf-8')
            elif jdata is not None:
                await self.log(self.host, 'restconf', 'request', rid=rid,
                               method=method, url=url, data=json.dumps(jdata))
            else:
                await self.log(self.host, 'restconf', 'request', rid=rid,
                               method=method, url=url)
            async with self.client.request(method, url, headers=self.headers,
                                           data=data, json=jdata) as response:
                if response.status in [201, 204]:
                    data = None  # No content is expected.
                else:
                    if response.headers['Content-Type'] == 'application/yang-data+json':
                        # data = await response.json()
                        data = await response.text()
                    else:
                        data = await response.text()
                await self.log(self.host, 'restconf', 'response',
                               status=response.status, rid=rid,
                               url=url, data=data)
                res = 'ok' if response.status in expected_status else 'nok'
                return (rid, res, response.status, data)
        except Exception as e:
            return (rid, 'exception', repr(e))

    async def get_stream(self, stream):
        url = f'http://{self.host}/restconf/streams/{stream}/json'
        headers = HEADERS_STREAM.copy()
        add_authentication(headers, self.user, self.password)
        rid = await self.next_id()
        await self.log(self.host, 'restconf', 'stream', rid=rid, stream=stream,
                       method='GET', url=url)
        async with self.client.get(url, headers=headers) as response:
            await self.log(self.host, 'restconf', 'response', method='GET',
                           rid=rid, url=url, status=response.status)
            assert response.status == 200
            # TODO: Improve performance by using something better than a string?
            # TODO: Decode event according to standard:
            #       https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream
            #       section 9.2.6
            s = ""
            l = ""
            async for line in response.content:
                l = line.decode('utf-8').strip()
                if l == "":  # Assuming an emply lines is end of message
                    o = s  # json.loads(s)
                    s = ""
                    await self.log(self.host, 'restconf', 'stream', rid=rid,
                                   stream=stream, data=o)
                elif l[:6] == 'data: ':
                    s += l[6:]
                elif l[:1] == ':':  # To catch ': error :':
                    # NSO may report device-notifications temporarily
                    # unavailable
                    await self.log(self.host, 'restconf', 'stream', rid=rid,
                                   stream=stream, data=l)
                else:
                    raise Exception(f"ERROR: Unhandled event encoding {self.host} {response.status} {l}")
