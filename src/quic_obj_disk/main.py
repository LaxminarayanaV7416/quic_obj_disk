import os

import requests
from flask import Flask, Response, jsonify, make_response, request
from loguru import logger
from node.network_interface import DHTRouter, NetworkLayer
from node.node import StorageNode
from storage.metadata import PersistenceLayer

app = Flask(__name__)

# --- Configuration ---
NODE_ID = os.environ.get("NODE_ID", "node1")
BOOTSTRAP_PEERS = os.environ.get("BOOTSTRAP_PEERS", "").split(",")
BOOTSTRAP_PEERS = [p for p in BOOTSTRAP_PEERS if p]


# --- Network Implementation ---
class HttpNetwork(NetworkLayer):
    def send_message(self, target_node_address, message):
        try:
            url = f"http://{target_node_address}/internal/message"
            requests.post(url, json=message, timeout=2)
        except Exception as e:
            print(f"Failed to send to {target_node_address}: {e}")


# --- Initialization ---
persistence = PersistenceLayer(db_path=f"/data/{NODE_ID}.db")
network = HttpNetwork()
dht = DHTRouter(NODE_ID, {})
node = StorageNode(NODE_ID, persistence, network, dht)

if BOOTSTRAP_PEERS:
    logger.info(f"Bootstrapping with {BOOTSTRAP_PEERS}")
    node.join_network(BOOTSTRAP_PEERS)


# --- Helper: XML Responses ---
def dict_to_xml(tag, d):
    elem = f'<{tag} xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    for k, v in d.items():
        elem += f"<{k}>{v}</{k}>"
    elem += f"</{tag}>"
    return elem


# --- S3 Routes ---


@app.route("/", methods=["GET"])
def list_buckets():
    """AWS CLI 'ls' checks root"""
    # Return a dummy list of buckets for auth validation
    # In a real system, we would aggregate buckets from peers
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <ListAllMyBucketsResult>
      <Owner><ID>p2p_admin</ID><DisplayName>admin</DisplayName></Owner>
      <Buckets></Buckets>
    </ListAllMyBucketsResult>"""
    return Response(xml, mimetype="application/xml")


@app.route("/<bucket>", methods=["PUT", "HEAD", "GET"])
def bucket_ops(bucket):
    """Handle Bucket Creation and Existence Checks"""

    # HEAD: Check existence (aws s3 cp checks this)
    if request.method == "HEAD":
        exists = node.handle_check_bucket(bucket)
        if exists:
            return Response("", status=200)
        return Response("", status=404)

    # PUT: Create Bucket (aws s3 mb)
    if request.method == "PUT":
        node.handle_create_bucket(bucket)
        # S3 returns empty 200 OK for mb
        return Response("", status=200, headers={"Location": f"/{bucket}"})

    return Response("Not Implemented", status=501)


@app.route("/<bucket>/<path:key>", methods=["GET", "PUT", "POST", "DELETE"])
def object_ops(bucket, key):
    """Handle Object and Multipart Operations"""

    # 1. GET Object
    if request.method == "GET":
        obj = node.handle_client_get(bucket, key)
        if obj:
            return Response(
                obj.data, mimetype=obj.content_type, headers={"ETag": f'"{obj.etag}"'}
            )
        return Response("", status=404)

    # 2. PUT Operations
    if request.method == "PUT":
        # A. Multipart Upload Part
        # Query: ?partNumber=1&uploadId=...
        part_num = request.args.get("partNumber")
        upload_id = request.args.get("uploadId")

        if part_num and upload_id:
            data = request.data
            res = node.handle_multipart_part(bucket, upload_id, int(part_num), data)
            # S3 expects ETag in header, body is empty usually
            return Response("", headers={"ETag": f'"{res["etag"]}"'}, status=200)

        # B. Standard PutObject
        else:
            data = request.data
            c_type = request.headers.get("Content-Type", "application/octet-stream")
            res = node.handle_client_put(bucket, key, data, c_type)
            return Response("", headers={"ETag": f'"{res["etag"]}"'}, status=200)

    # 3. POST Operations (Multipart Init/Complete)
    if request.method == "POST":
        # A. Initiate Multipart (Key?uploads)
        if "uploads" in request.args:
            res = node.handle_multipart_init(bucket, key)
            xml = dict_to_xml(
                "InitiateMultipartUploadResult",
                {"Bucket": bucket, "Key": key, "UploadId": res["upload_id"]},
            )
            return Response(xml, mimetype="application/xml")

        # B. Complete Multipart (Key?uploadId=...)
        upload_id = request.args.get("uploadId")
        if upload_id:
            # AWS Sends an XML body of parts, we ignore it and trust our internal store
            res = node.handle_multipart_complete(bucket, upload_id)
            if "error" in res:
                return Response(
                    f"<Error><Message>{res['error']}</Message></Error>",
                    status=400,
                    mimetype="application/xml",
                )

            xml = dict_to_xml(
                "CompleteMultipartUploadResult",
                {
                    "Location": res["location"],
                    "Bucket": res["bucket"],
                    "Key": res["key"],
                    "ETag": f'"{res["etag"]}"',
                },
            )
            return Response(xml, mimetype="application/xml")

    # 4. DELETE Object
    if request.method == "DELETE":
        # Standard DELETE not implemented in this demo update, but easy to add
        return Response("", status=204)

    return Response("Not Implemented", status=501)


# --- Internal RPC (Peer Communication) ---
@app.route("/internal/message", methods=["POST"])
def internal_message():
    msg = request.json
    if msg["type"] == "HELLO":
        node.handle_hello(msg["sender_id"], msg["sender_addr"])
    elif msg["type"] == "STORE_OBJECT" or msg["type"] == "CREATE_BUCKET":
        node.on_peer_message(msg)
    return "OK", 200


if __name__ == "__main__":
    # Disable Flask banner to keep logs clean
    app.run(host="0.0.0.0", port=5000)
