"""Minimal AES WTI Make Predictive Call client."""

import argparse
import json
import sys
from typing import Optional

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning


AES_SERVER: Optional[str] = "192.168.122.25"
USERNAME: Optional[str] = "cust"
PASSWORD: Optional[str] = "aes10_cmb@Dm1n"


def _api_url(aes_server, path):
    base_url = aes_server.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    if not base_url.endswith("/api"):
        base_url = f"{base_url}/api"
    return f"{base_url}{path}"


def _raise_for_status(response):
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


def make_predictive_call(
    calling_device,
    called_directory_number,
    aes_server: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    insecure=False,
):
    """Initiate an AES Make Predictive Call and return its JSON response."""
    aes_server = aes_server if aes_server is not None else AES_SERVER
    username = username if username is not None else USERNAME
    password = password if password is not None else PASSWORD
    if aes_server is None or username is None or password is None:
        raise ValueError("AES server, username, and password are required")

    verify = not insecure
    if insecure:
        urllib3.disable_warnings(InsecureRequestWarning)
    session_url = _api_url(aes_server, "/fe/v1/ApplicationSession")
    call_url = _api_url(aes_server, "/fe/v1/MakePredictiveCall")
    token = None
    session_id = None

    try:
        session_response = requests.post(
            session_url, auth=(username, password), json={}, verify=verify
        )
        _raise_for_status(session_response)
        session = session_response.json()
        token = session.get("token")
        session_id = session.get("sessionID")
        if not token or not session_id:
            raise ValueError("AES session response is missing token or sessionID")

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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Initiate an AES Make Predictive Call."
    )
    parser.add_argument("calling_device")
    parser.add_argument("called_directory_number")
    parser.add_argument("--aes-server")
    parser.add_argument("--username")
    parser.add_argument("--password", help="Visible in shell history and process listings.")
    parser.add_argument(
        "--insecure", action="store_true", help="Disable TLS certificate verification."
    )
    args = parser.parse_args(argv)

    try:
        response = make_predictive_call(
            args.calling_device,
            args.called_directory_number,
            aes_server=args.aes_server,
            username=args.username,
            password=args.password,
            insecure=args.insecure,
        )
    except (requests.RequestException, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    #sys.argv.extend(["--insecure", "1001", "1002"])
    raise SystemExit(main())
