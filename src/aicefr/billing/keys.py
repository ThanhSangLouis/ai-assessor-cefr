"""Licence keys, for contracts paid outside the system (D033).

Most institutions pay against a contract and an invoice, not on a card page.
For them the provider issues a key that the administrator pastes in:
`AICEFR1.<payload>.<signature>`, where the payload is the licence as JSON in
base64url and the signature is HMAC-SHA256 of the payload with the licence
secret (`AICEFR_LICENSE_SECRET`).

The limit of HMAC is said here rather than hidden: whoever holds the secret
can sign, so a key proves nothing to a deployment the institution runs on its
own machine, where it can read the secret. That is fine where the provider runs
the server; on premises an asymmetric signature (Ed25519) would be needed,
which means a new dependency and is left for when it is approved (proposal,
mục 4.3).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date

from aicefr.billing.plans import MAX_SEATS, PURCHASABLE, License, Plan
from aicefr.encoding import b64url_decode as _unb64
from aicefr.encoding import b64url_encode as _b64

PREFIX = "AICEFR1"


class LicenseKeyError(ValueError):
    """A key that cannot be installed; the message says why, in Vietnamese."""


def _sign(payload: str, secret: bytes) -> str:
    return _b64(hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest())


def issue(license: License, secret: bytes, issued_at: str) -> str:
    """The key for a licence. Run by the provider, never by the deployment it is for."""
    body = {
        "v": 1,
        "license_id": license.license_id,
        "organization": license.organization,
        "plan": license.plan.value,
        "seats": license.seats,
        "valid_from": license.valid_from.isoformat(),
        "valid_to": license.valid_to.isoformat(),
        "issued_at": issued_at,
    }
    payload = _b64(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return f"{PREFIX}.{payload}.{_sign(payload, secret)}"


def read(key: str, secret: bytes) -> License:
    """The licence a key carries, once its signature and contents check out."""
    parts = key.strip().split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        raise LicenseKeyError("mã giấy phép không đúng định dạng")
    _prefix, payload, signature = parts
    if not hmac.compare_digest(_sign(payload, secret), signature):
        raise LicenseKeyError("chữ ký của mã giấy phép không khớp")
    try:
        body = json.loads(_unb64(payload).decode("utf-8"))
        lic = License(
            license_id=str(body["license_id"]),
            organization=str(body["organization"]).strip(),
            plan=Plan(body["plan"]),
            seats=int(body["seats"]),
            valid_from=date.fromisoformat(body["valid_from"]),
            valid_to=date.fromisoformat(body["valid_to"]),
            source="key",
        )
    except (ValueError, KeyError, TypeError) as e:
        raise LicenseKeyError("nội dung mã giấy phép không đọc được") from e
    if lic.plan not in PURCHASABLE or not 1 <= lic.seats <= MAX_SEATS:
        raise LicenseKeyError("mã giấy phép ghi gói hoặc số sinh viên không hợp lệ")
    if lic.valid_to < lic.valid_from or not lic.license_id or not lic.organization:
        raise LicenseKeyError("mã giấy phép thiếu tổ chức, mã hoặc thời hạn hợp lệ")
    return lic
