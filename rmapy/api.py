import requests
import json
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from logging import getLogger
from datetime import datetime
from typing import Union, Optional, Dict, TypedDict, List
from dataclasses import dataclass, field
from uuid import uuid4
from .config import load, dump
from .types import (
    FileMetaBlob,
    FileMetaListBlob,
    RawFileBlob,
    RawJsonBlob,
    Document,
    Collection,
    RootFolder,
    AbstractBlob,
)
from .exceptions import (
    AuthError,
    DocumentNotFound,
    ApiError,
    UnsupportedTypeError,)
from .const import (RFC3339Nano,
                    USER_AGENT,
                    BASE_URL,
                    DEVICE_TOKEN_URL,
                    USER_TOKEN_URL,
                    TECTONIC_URL,
                    DEVICE,)

log = getLogger("rmapy")

def requests_session_with_retry():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)

    return session

class Client(object):
    """API Client for Remarkable Cloud

    This allows you to authenticate & communicate with the Remarkable Cloud
    and does all the heavy lifting for you.
    """

    token_set = {
        "devicetoken": "",
        "usertoken": ""
    }

    verify = True

    def __init__(self):
        config = load()
        if "devicetoken" in config:
            self.token_set["devicetoken"] = config["devicetoken"]
        if "usertoken" in config:
            self.token_set["usertoken"] = config["usertoken"]
        self.session = requests_session_with_retry()

    def request(self, method: str, path: str,
                data=None,
                body=None, headers=None,
                params=None, stream=False, retry=True) -> requests.Response:
        """Creates a request against the Remarkable Cloud API

        This function automatically fills in the blanks of base
        url & authentication.

        Args:
            method: The request method.
            path: complete url or path to request.
            data: raw data to put/post/...
            body: the body to request with. This will be converted to json.
            headers: a dict of additional headers to add to the request.
            params: Query params to append to the request.
            stream: Should the response be a stream?
        Returns:
            A Response instance containing most likely the response from
            the server.
        """

        if headers is None:
            headers = {}
        if not path.startswith("http"):
            if not path.startswith('/'):
                path = '/' + path
            url = f"{BASE_URL}{path}"
        else:
            url = path

        _headers = {
            "user-agent": USER_AGENT,
        }

        if self.token_set["usertoken"]:
            token = self.token_set["usertoken"]
            _headers["Authorization"] = f"Bearer {token}"
        for k in headers.keys():
            _headers[k] = headers[k]
        log.debug(url, _headers)
        r = self.session.request(method, url,
                            json=body,
                            data=data,
                            headers=_headers,
                            params=params,
                            stream=stream,
                            verify=self.verify)
        if r.status_code == 401:
            if retry:
                log.warn(f"Unauthorized, renewing token: {r.text}")
                self.renew_token()
                return self.request(method, path, data, body, headers, params, stream, retry=False)
            else:
                raise AuthError(f"Unauthorized: {r.text}")

        return r

    def register_device(self, code: str):
        """Registers a device on the Remarkable Cloud.

        This uses a unique code the user gets from
        https://my.remarkable.com/device/desktop/connect to register
        a new device or client to be able to execute api calls.

        Args:
            code: A unique One time code the user can get
                at https://my.remarkable.com/device/desktop/connect.
        Returns:
            True
        Raises:
            AuthError: We didn't recieved an devicetoken from the Remarkable
                Cloud.
        """

        uuid = str(uuid4())
        body = {
            "code": code,
            "deviceDesc": DEVICE,
            "deviceID": uuid,

        }
        response = self.request("POST", DEVICE_TOKEN_URL, body=body)
        if response.ok:
            self.token_set["devicetoken"] = response.text
            dump(self.token_set)
            return True
        else:
            raise AuthError("Can't register device")

    def renew_token(self):
        """Fetches a new user_token.

        This is the second step of the authentication of the Remarkable Cloud.
        Before each new session, you should fetch a new user token.
        User tokens have an unknown expiration date.

        Returns:
            True

        Raises:
            AuthError: An error occurred while renewing the user token.
        """

        if not self.token_set["devicetoken"]:
            raise AuthError("Please register a device first")
        token = self.token_set["devicetoken"]
        response = self.request("POST", USER_TOKEN_URL, None, headers={
                "Authorization": f"Bearer {token}"
            })
        if response.ok:
            self.token_set["usertoken"] = response.text
            dump(self.token_set)
            return True
        else:
            raise AuthError("Can't renew token: {e}".format(
                e=response.status_code))

    def is_auth(self) -> bool:
        """Is the client authenticated

        Returns:
            bool: True if the client is authenticated
        """

        if self.token_set["devicetoken"] and self.token_set["usertoken"]:
            return True
        else:
            return False
    
    def get_root_folder(self) -> RootFolder:
        """Returns the root folder with caching.
        
        Returns:
            Folder
        """

        hash = self.get_root_hash()
        root_meta = self.get_blob(hash)
        return RootFolder(
            client = self,
            hash = hash,
            list_blob = root_meta
        )

    def get_root_hash(self) -> str:
        """Returns the root hash ID.

        Returns:
            str
        """

        response = self.request("GET", f"{TECTONIC_URL}/sync/v4/root")
        j = response.json()
        log.debug(f"root data: {j}")
        if not j or not j.get("hash"):
            return None
        return j.get("hash")

    def get_blob(self, _hash: str) -> AbstractBlob:
        """
        Get a blob by ID. 

        Args:
            _hash: The hash of the meta item.

        Returns:
            An AbstractBlob or None
        """

        log.debug(f"Getting blob {_hash}")
        response = self.request("GET", f"{TECTONIC_URL}/sync/v3/files/{_hash}",
                                params={})
        log.debug(response.url)

        if response.status_code//100 == 4:
            return None

        contentType = response.headers['content-type']
        if contentType.startswith('text/'):
            data_lines = response.text.splitlines()

            if data_lines[0].strip()[0] == '{':
                # JSON
                return RawJsonBlob(
                    client = self,
                    json = json.loads(''.join(data_lines))
                )
            elif len(data_lines) > 1 and data_lines[1].count(':') >= 4:
                # List of files
                items = []
                for line in data_lines[1:]:
                    hash, _, name, _, size = line.split(':')
                    items.append(FileMetaBlob(
                        client = self,
                        hash = hash,
                        name = name,
                        size = size
                    ))

                return FileMetaListBlob(
                    client = self,
                    files = items
                )
        else:
            return RawFileBlob(
                client = self,
                contentType = contentType,
                content = response.content
            )
    