import grpc
import time
import os_statistics_pb2
import os_statistics_pb2_grpc


def get_statistics(stub):
    response = stub.GetMachineName(os_statistics_pb2.google_dot_protobuf_dot_empty__pb2.Empty())
    pid = os_statistics_pb2.PID(pid=<Your PID>)  
    stub.StartMonitoringService(pid)
    time.sleep(100)
    response = stub.GetStatistics(os_statistics_pb2.google_dot_protobuf_dot_empty__pb2.Empty())


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = os_statistics_pb2_grpc.OSStatisticsServiceStub(channel)
        get_statistics(stub)


class Statistics:
    def __init__(self):
        self.total_cpu_usage = None
        self.memory = None


if __name__ == '__main__':
    run()
