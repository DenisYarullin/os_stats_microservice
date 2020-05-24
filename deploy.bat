#!/bin/bash
python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/os_statistics.proto