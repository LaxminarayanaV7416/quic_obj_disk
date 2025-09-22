"""
Author: Laxminarayana Vadnala
Date: Sep 21, 2025
Description: RPC server for handling client requests.
Email: lvadnala@nd.edu
"""

import os
import asyncio
import logging
from typing import Optional, Any
import argparse
from concurrent import futures
import grpc
import time

# we will import protobuf generated classes
from heartBeat_pb2_grpc import workerHeartBeatServiceStub
import heartBeat_pb2 as heartBeat_pb2

WORKER_ID = os.getenv("WORKER_ID", "worker_1")


def open_file_util(path: str) -> str:
    """
    Utility function to read file contents.
    """
    if os.path.exists(path):
        with open(path, "rb") as file:
            return file.read()
    else:
        raise FileNotFoundError(f"File at path {path} does not exist.")


async def client(
    host: str = "localhost",
    port: int = 50051,
    secure_channel: bool = False,
    certificate: Optional[Any] = None,
) -> None:
    """
    Starts the gRPC client to handle server requests.
    Args:
        host (str): The server host address to listen on.
        port (int): The port number to listen on.
        secure_channel (bool): Whether to use a secure channel.
        certificate (Optional[Any]): The SSL certificate for secure channel.
    """
    try:
        host_port = f"{host}:{port}"
        if secure_channel:
            channel = grpc.secure_channel(host_port, certificate)
            stub = workerHeartBeatServiceStub(channel)
            logging.info(f"Connected to secure gRPC server at {host_port}")
        else:
            channel = grpc.insecure_channel(host_port)
            stub = workerHeartBeatServiceStub(channel)
            logging.info(f"Connected to insecure gRPC server at {host_port}")
        response = stub.sendHeartBeat(
            heartBeat_pb2.workerHeartBeat(
                workerNumber=1, alive=True, timestamp=int(time.time())
            )
        )
        logging.info(
            f"Heartbeat response from message: {response.recievedHeartBeat}"
        )
    finally:
        channel.close()


def argument_parser() -> argparse.Namespace:
    """
    Parses command line arguments.
    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="RPC Server")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host name to connect to, Usually server host name",
    )
    parser.add_argument(
        "--port", type=int, default=50051, help="Server Port number to listen on"
    )
    parser.add_argument("--secure", action="store_true", help="Use secure channel")
    parser.add_argument(
        "--cert", type=str, help="Path to SSL certificate", required=False
    )
    return parser.parse_args()


def main():
    """
    Main function to start the server.
    """
    args = argument_parser()
    logging.basicConfig(level=logging.INFO)
    if args.secure:
        certificate = open_file_util(args.cert)
        client_certificate = grpc.ssl_server_credentials(root_certificates=certificate)

        try:
            asyncio.run(
                client(
                    host=args.host,
                    port=args.port,
                    secure_channel=True,
                    certificate=client_certificate,
                )
            )
        except KeyboardInterrupt:
            logging.info("Client stopped by user")
    else:
        try:
            asyncio.run(client(host=args.host, port=args.port))
        except KeyboardInterrupt:
            logging.info("client stopped by user")


if __name__ == "__main__":
    main()
