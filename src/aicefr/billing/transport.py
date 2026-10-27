"""How billing code calls a gateway's server: HTTPS through the standard library (D035).

Two gateways must call out. Stripe opens a Checkout Session and reads it back;
MoMo opens a payment. Each takes a `Transport`, and the tests hand it a fake,
so no test ever reaches the network. There is no new dependency: a few JSON or
form requests a day need nothing more than `urllib.request`.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass

TIMEOUT_S = 15


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is handed back as a reply, not followed.

    urllib would follow it carrying every header but the content ones --
    `Authorization: Bearer sk_…` included -- to whatever host it names.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


@dataclass(frozen=True)
class Reply:
    status: int
    body: bytes


# (method, url, headers, body) -> the gateway's reply, whatever its status.
Transport = Callable[[str, str, Mapping[str, str], "bytes | None"], Reply]


class Unreachable(Exception):
    """No answer at all: DNS, TLS, a refused connection, a timeout."""


def https(method: str, url: str, headers: Mapping[str, str], body: bytes | None) -> Reply:
    """Send one request and return the reply; an HTTP error status is a reply, not an exception."""
    if not url.startswith("https://"):
        raise ValueError("a gateway is only ever called over https")
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    try:
        with _OPENER.open(request, timeout=TIMEOUT_S) as response:
            return Reply(response.status, response.read())
    except urllib.error.HTTPError as e:
        return Reply(e.code, e.read())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Unreachable(type(e).__name__) from e
