"""Interactively verify an existing account without printing or storing credentials."""

import argparse
from getpass import getpass
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1", help="API base URL")
    args = parser.parse_args()

    def request(path, payload=None, token=None):
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = Request(args.url.rstrip("/") + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        try:
            with urlopen(req, timeout=30) as response:
                print(f"{req.get_method()} {path}: HTTP {response.status}")
                return json.load(response)["data"]
        except HTTPError as exc:
            raise SystemExit(f"{req.get_method()} {path}: HTTP {exc.code}. No credentials or tokens were printed.") from None
        except URLError:
            raise SystemExit("Unable to reach the API. Check that FastAPI is running at the supplied URL.") from None

    tokens = request("/auth/login", {"email": input("Existing account email: ").strip(), "password": getpass("Password (hidden): ")})
    profile = request("/auth/users/me", token=tokens["access_token"])
    if not profile.get("is_active") or not profile.get("created_at") or not profile.get("updated_at"):
        raise SystemExit("The server returned an incomplete account profile.")
    renewed = request("/auth/refresh", {"refresh_token": tokens["refresh_token"]})
    request("/auth/users/me", token=renewed["access_token"])
    request("/auth/logout", {})
    print("Existing-account login, complete profile, refresh, and logout verified.")


if __name__ == "__main__":
    main()
