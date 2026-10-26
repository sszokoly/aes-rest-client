"""Minimal AES WTI Make Call and Make Predictive Call client."""

import argparse
import json
import sys
from typing import Optional

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning


AES_SERVER: Optional[str] = ""
USERNAME: Optional[str] = ""
PASSWORD: Optional[str] = ""
SWITCH_NAME: Optional[str] = ""


def _api_url(aes_server: str, path: str) -> str:
    base_url = aes_server.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    if not base_url.endswith("/api"):
        base_url = f"{base_url}/api"
    return f"{base_url}{path}"


def _raise_for_status(response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            details = response.json()
        except ValueError:
            raise
        if isinstance(details, dict) and details:
            description = ", ".join(f"{key}={value}" for key, value in details.items())
            raise requests.HTTPError(
                f"{error}: AES error: {description}", response=response
            ) from error
        raise


def _resolve_device_id(
    device: str, switch_name: str, call_url: str, token: str, verify: bool
) -> str:
    if ":" in device:
        return device

    response = requests.post(
        call_url.rsplit("/", 1)[0] + "/GetThirdPartyDeviceId",
        headers={"Authorization": f"Bearer {token}"},
        json={"switchName": switch_name, "extension": device},
        verify=verify,
    )
    _raise_for_status(response)
    device_id = response.json().get("GetThirdPartyDeviceIdResponse", {}).get("device")
    if not device_id:
        raise ValueError(f"AES did not return a device ID for {device}")
    return device_id


def _call_service(
    endpoint: str,
    calling_device: str,
    called_directory_number: str,
    aes_server: Optional[str],
    username: Optional[str],
    password: Optional[str],
    insecure: bool,
    switch_name: Optional[str],
):
    aes_server = aes_server if aes_server is not None else AES_SERVER
    username = username if username is not None else USERNAME
    password = password if password is not None else PASSWORD
    switch_name = switch_name if switch_name is not None else SWITCH_NAME
    if aes_server is None or username is None or password is None:
        raise ValueError("AES server, username, and password are required")
    if not switch_name:
        raise ValueError("AES switch name is required")

    verify = not insecure
    if insecure:
        urllib3.disable_warnings(InsecureRequestWarning)
    session_url = _api_url(aes_server, "/session")
    call_url = _api_url(aes_server, endpoint)
    token = None
    session_id = None

    try:
        session_response = requests.post(
            session_url,
            auth=(username, password),
            json={"switchName": switch_name},
            verify=verify,
        )
        _raise_for_status(session_response)
        session = session_response.json()
        token = session.get("token")
        session_id = session.get("sessionID")
        if not token or not session_id:
            raise ValueError("AES session response is missing token or sessionID")

        calling_device = _resolve_device_id(
            calling_device, switch_name, call_url, token, verify
        )
        called_directory_number = _resolve_device_id(
            called_directory_number, switch_name, call_url, token, verify
        )

        call_response = requests.post(
            call_url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "callingDevice": calling_device,
                "calledDirectoryNumber": called_directory_number,
            },
            verify=verify,
        )
        _raise_for_status(call_response)
        return call_response.json()
    finally:
        if token and session_id:
            try:
                requests.delete(
                    session_url,
                    headers={"Authorization": f"Bearer {token}"},
                    json={"sessionID": session_id},
                    verify=verify,
                )
            except requests.RequestException:
                pass


def make_call(
    calling_device: str,
    called_directory_number: str,
    aes_server: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    insecure: bool = False,
    switch_name: Optional[str] = None,
):
    """Initiate an AES Make Call and return its JSON response."""
    return _call_service(
        "/fe/v1/MakeCall",
        calling_device,
        called_directory_number,
        aes_server,
        username,
        password,
        insecure,
        switch_name,
    )


def make_predictive_call(
    calling_device: str,
    called_directory_number: str,
    aes_server: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    insecure: bool = False,
    switch_name: Optional[str] = None,
):
    """Initiate an AES Make Predictive Call and return its JSON response.

    AES requires a TSAPI Advanced tier: VALUE_AES_AEC_SMALL_ADVANCED,
    VALUE_AES_AEC_MEDIUM_ADVANCED, or VALUE_AES_AEC_LARGE_ADVANCED.
    """
    return _call_service(
        "/fe/v1/MakePredictiveCall",
        calling_device,
        called_directory_number,
        aes_server,
        username,
        password,
        insecure,
        switch_name,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Initiate an AES call.")
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument("--make-call", action="store_true")
    operations.add_argument("--make-predictive-call", action="store_true")
    parser.add_argument("calling_device")
    parser.add_argument("called_directory_number")
    parser.add_argument("--aes-server", help="AES server URL or IP address.")
    parser.add_argument("--username", help="AES CTI user name.")
    parser.add_argument("--password", help="AES CTI user password.")
    parser.add_argument("--switch-name", help="AES CM switch connection name.")
    parser.add_argument(
        "--insecure", action="store_true", help="Disable TLS certificate verification."
    )
    args = parser.parse_args(argv)

    operation = make_call if args.make_call else make_predictive_call
    try:
        response = operation(
            args.calling_device,
            args.called_directory_number,
            aes_server=args.aes_server,
            username=args.username,
            password=args.password,
            insecure=args.insecure,
            switch_name=args.switch_name,
        )
    except (requests.RequestException, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
