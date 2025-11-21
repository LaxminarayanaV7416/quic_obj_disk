import hashlib
import hmac
import urllib.parse

from config import ALLOW_ANON, KEYS

# TODO work on defining the Exception and status code
from fastapi import HTTPException, status


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def derive_signing_key(
    secret_key: str, amz_date: str, region: str, service: str
) -> bytes:
    date_stamp = amz_date[:8]
    k_date = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


def parse_auth_header(auth: str) -> dict[str, str]:
    scheme, rest = auth.split(" ", 1)
    parts: dict[str, str] = {}
    for kv in rest.split(","):
        k, v = kv.strip().split("=", 1)
        parts[k] = v
    cred = parts["Credential"].split("/")
    parts["access_key_id"] = cred[0]
    parts["date"] = cred[1]
    parts["region"] = cred[2]
    parts["service"] = cred[3]
    parts["terminal"] = cred[4]
    return parts


def build_canonical_request(
    method: str,
    path: str,
    query: str,
    headers: dict[str, str],
    signed_headers: str,
    payload_hash: str,
) -> str:
    canonical_uri = path if path else "/"
    canonical_querystring = query or ""
    hdrs = {k.lower().strip(): " ".join(v.strip().split()) for k, v in headers.items()}
    signed_set = set(signed_headers.split(";"))
    # Include only signed headers in canonical_headers
    selected = [(k, hdrs.get(k, "")) for k in sorted(hdrs.keys()) if k in signed_set]
    canonical_headers = "".join([f"{k}:{v}\n" for k, v in selected])
    return "\n".join(
        [
            method,
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )


def build_string_to_sign(
    amz_date: str, credential_scope: str, canonical_request: str
) -> str:
    cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    return "\n".join(["AWS4-HMAC-SHA256", amz_date, credential_scope, cr_hash])


async def require_sigv4(headers: dict[str, str], body: bytes, method: str, url: str):
    if ALLOW_ANON:
        return
    auth = headers.get("Authorization")
    amz_date = headers.get("x-amz-date")
    payload_hash = headers.get("x-amz-content-sha256", "")
    if not auth or not amz_date or not payload_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AccessDenied: Missing SigV4 headers",
        )

    params = parse_auth_header(auth)
    access_key_id = params["access_key_id"]
    secret_key = KEYS.get(access_key_id)
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="InvalidAccessKeyId"
        )

    if payload_hash != "UNSIGNED-PAYLOAD":
        calc = hashlib.sha256(body or b"").hexdigest()
        if payload_hash != calc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="XAmzContentSHA256Mismatch",
            )

    signed_headers = params["SignedHeaders"]
    credential_scope = "/".join(
        [params["date"], params["region"], params["service"], params["terminal"]]
    )
    urllib_url = urllib.parse.urlsplit(url)
    canonical_request = build_canonical_request(
        method, urllib_url.path, urllib_url.query, headers, signed_headers, payload_hash
    )
    string_to_sign = build_string_to_sign(amz_date, credential_scope, canonical_request)
    signing_key = derive_signing_key(
        secret_key, amz_date, params["region"], params["service"]
    )
    expected_sig = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if expected_sig != params["Signature"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="SignatureDoesNotMatch"
        )
