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
# we will import protobuf generated classes
from heartBeat_pb2_grpc import workerHeartBeatServiceServicer
import heartBeat_pb2 as heartBeat_pb2


class workerHeartBeatServiceServicerImplmentation(workerHeartBeatServiceServicer):
    def __init__(self):
        super().__init__()

    async def sendHeartBeat(
            self, 
            request: heartBeat_pb2.workerHeartBeat, 
            context: grpc.aio.ServicerContext
        ) -> heartBeat_pb2.mastersHeartBeatResponse:
        logging.info(f"Received heartbeat from worker ID: {request.worker_id}")
        # Process the heartbeat (e.g., update worker status in a database)
        #TODO: Need work here what to do we will figure it out later
        response = heartBeat_pb2.mastersHeartBeatResponse( recieved_heart_beat=True )
        return response


def open_file_util(path: str)-> str:
    if os.path.exists(path):
        with open(path, 'rb') as file:
            return file.read()
    else:
        raise FileNotFoundError(f"File at path {path} does not exist.")

async def server(port: int = 50051,
                 secure_channel: bool = False,
                 max_workers: int = 4,
                 certificate: Optional[Any] = None) -> None:
    """
    Starts the gRPC server to handle client requests.
    Args:
        port (int): The port number to listen on.
        secure_channel (bool): Whether to use a secure channel.
        certificate (Optional[Any]): The SSL certificate for secure channel.
    """
    if secure_channel:
        server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        server_credentials = certificate
        server.add_secure_port(f'[::]:{port}', server_credentials)
        logging.info(f"Starting secure gRPC server on port {port} which is SECURE")
    else:
        server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        server.add_insecure_port(f'[::]:{port}')
        logging.info(f"Starting insecure gRPC server on port {port} which is INSECURE")
    await server.start()
    logging.info("Server started successfully")
    await server.wait_for_termination()



def argument_parser() -> argparse.Namespace:
    """
    Parses command line arguments.
    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="RPC Server")
    parser.add_argument("--port", type=int, default=50051, help="Port number to listen on")
    parser.add_argument("--secure", action="store_true", help="Use secure channel")
    parser.add_argument("--cert", type=str, help="Path to SSL certificate", required=False)
    parser.add_argument("--cert-key", type=str, help="Path to SSL certificate key", required=False)
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum number of worker threads")
    return parser.parse_args()

def main():
    """
    Main function to start the server.
    """
    args = argument_parser()
    logging.basicConfig(level=logging.INFO)
    if args.secure:
        certificate = open_file_util(args.cert)
        private_key  = open_file_util(args.cert_key)
        server_credentials = grpc.ssl_server_credentials([(private_key, certificate)])
        try:
            asyncio.run(server(port=args.port, 
                               secure_channel=True,
                                certificate=server_credentials))
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
    else:
        try:
            asyncio.run(server(port=args.port, secure_channel=False))
        except KeyboardInterrupt:
            logging.info("Server stopped by user")

if __name__ == "__main__":
    main()