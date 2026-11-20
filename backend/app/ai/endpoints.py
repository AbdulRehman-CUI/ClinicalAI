"""Public-only, DNS-pinned transport for untrusted OpenAI-compatible URLs."""
import ipaddress
import socket
from urllib.parse import urlsplit
import httpx
from app.services.exceptions import LLMRequestError


def validate_endpoint(value: str) -> str:
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.port not in (None, 443)
                or "\\" in value or any(ord(c) < 33 for c in value)):
            raise ValueError()
        return value.rstrip("/")
    except ValueError:
        raise LLMRequestError("llm_endpoint_invalid", "Use an HTTPS base URL on port 443 without credentials, query or fragment.", 422) from None


def public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or value == "168.63.129.16":
        return False
    if isinstance(address, ipaddress.IPv6Address):
        # Translation/tunnel ranges can encode an otherwise forbidden IPv4 target.
        if address.sixtofour or address.teredo or address in ipaddress.ip_network("64:ff9b::/96") or address in ipaddress.ip_network("64:ff9b:1::/48"):
            return False
    return True


class PublicEndpointTransport(httpx.HTTPTransport):
    def handle_request(self, request):
        host = request.url.host
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
            if not addresses or any(not public_address(ip) for ip in addresses):
                raise ValueError()
        except (ValueError, OSError):
            raise LLMRequestError("llm_endpoint_blocked", "Endpoint must resolve only to public internet addresses.", 422) from None
        # Connect to the checked IP, retaining the original TLS identity and Host.
        request.headers["Host"] = host
        request.extensions["sni_hostname"] = host
        request.url = request.url.copy_with(host=sorted(addresses)[0])
        return super().handle_request(request)
