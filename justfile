test:
    @echo "Welcome to Just Trails"

build-protobuf:
    python -m grpc_tools.protoc -I./networks/rpc/protos --python_out=./networks/rpc --grpc_python_out=./networks/rpc ./networks/rpc/protos/*.proto