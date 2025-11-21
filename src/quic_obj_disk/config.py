import os

BASE_DIR = os.path.abspath(os.getcwd())

WORKERS = os.environ.get(
    "S3_WORKERS", "http://127.0.0.1:9101,http://127.0.0.1:9102"
).split(",")
ALLOW_ANON = os.environ.get("S3_ALLOW_ANON", "false").lower() == "true"

# SigV4 credentials: must match your AWS CLI profile used for requests
KEYS: dict[str, str] = {
    os.environ.get("AWS_ACCESS_KEY_ID", "local-access-key"): os.environ.get(
        "AWS_SECRET_ACCESS_KEY", "local-secret-key"
    )
}
