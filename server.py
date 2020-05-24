from concurrent import futures
import psutil
import grpc
import cpuinfo
import logging
import platform
from threading import Event, Thread

import os_statistics_pb2
import os_statistics_pb2_grpc


def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


def get_size_as_float_need_suffix(bytes, suffix="M"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if unit == suffix:
            return float(f"{bytes:.2f}")
        bytes /= factor


class Statistics:
    def __init__(self):
        self.total_cpu_usage = 0.0
        self.cpu_usage_per_core = None
        self.memory_available = 0.0
        self.memory_used = 0.0
        self.memory_percentage = 0.0
        self.process_info_cpu_percent = 0.0
        self.process_info_rss = 0.0
        self.process_info_vms = 0.0
        self.process_info_uss = 0.0
        self.process_info_pss = 0.0
        self.process_info_memory_percent_rss = 0.0
        self.process_info_memory_percent_vms = 0.0
        self.process_info_memory_percent_uss = 0.0
        self.process_info_memory_percent_pss = 0.0


class StatisticsService(os_statistics_pb2_grpc.OSStatisticsServiceServicer):

    def __init__(self):
        self.pid = None
        self.memory_total = None
        self.statistics = Statistics()
        self.event = Event()

    def CollectStatistics(self):

        while not self.event.is_set():

            current_cpu_percent = psutil.cpu_percent(interval=1)
            current_cpu_usage_per_core = psutil.cpu_percent(interval=1, percpu=True)
            if current_cpu_percent > self.statistics.total_cpu_usage:
                self.statistics.total_cpu_usage = current_cpu_percent
                self.statistics.cpu_usage_per_core = current_cpu_usage_per_core

            svmem = psutil.virtual_memory()
            self.memory_total = svmem.total

            current_memory_available = svmem.available
            if current_memory_available < self.statistics.memory_available:
                self.statistics.memory_available = current_memory_available

            current_memory_used = svmem.used
            if current_memory_used > self.statistics.memory_used:
                self.statistics.memory_used = current_memory_used

            current_memory_percentage = svmem.percent
            if current_memory_percentage > self.statistics.memory_percentage:
                self.statistics.memory_percentage = current_memory_percentage

            p = psutil.Process(self.pid)

            current_process_info_cpu_percent = p.cpu_percent(interval=1.0)
            if current_process_info_cpu_percent > self.statistics.process_info_cpu_percent:
                self.statistics.process_info_cpu_percent = current_process_info_cpu_percent

            mem = p.memory_full_info()

            current_process_info_rss = mem.rss
            if current_process_info_rss > self.statistics.process_info_rss:
                self.statistics.process_info_rss = current_process_info_rss

            current_process_info_vms = mem.vms
            if current_process_info_vms > self.statistics.process_info_vms:
                self.statistics.process_info_vms = current_process_info_vms

            current_process_info_uss = mem.uss
            if current_process_info_uss > self.statistics.process_info_uss:
                self.statistics.process_info_uss = current_process_info_uss

            if platform == "linux" or platform == "linux2":
                current_process_info_pss = mem.pss
                if current_process_info_pss > self.statistics.process_info_pss:
                    self.statistics.process_info_pss = current_process_info_pss

            current_process_info_memory_percent_rss = p.memory_percent(memtype="rss")
            if current_process_info_memory_percent_rss > self.statistics.process_info_memory_percent_rss:
                self.statistics.process_info_memory_percent_rss = current_process_info_memory_percent_rss

            current_process_info_memory_percent_vms = p.memory_percent(memtype="vms")
            if current_process_info_memory_percent_vms > self.statistics.process_info_memory_percent_vms:
                self.statistics.process_info_memory_percent_vms = current_process_info_memory_percent_vms

            current_process_info_memory_percent_uss = p.memory_percent(memtype="uss")
            if current_process_info_memory_percent_uss > self.statistics.process_info_memory_percent_uss:
                self.statistics.process_info_memory_percent_uss = current_process_info_memory_percent_uss

            if platform == "linux" or platform == "linux2":
                current_process_info_memory_percent_pss = p.memory_percent(memtype="pss")
                if current_process_info_memory_percent_pss > self.statistics.process_info_memory_percent_pss:
                    self.statistics.process_info_memory_percent_pss = current_process_info_memory_percent_pss

    def StartMonitoringService(self, request, context):
        self.statistics = Statistics()
        self.event.clear()
        self.pid = request.pid
        microphone_thread = Thread(target=self.CollectStatistics)
        microphone_thread.start()
        return os_statistics_pb2.google_dot_protobuf_dot_empty__pb2.Empty()

    def GetMachineName(self, request, context):
        header = "Server\nOS Name"
        if platform.system() == "Windows":
            header += " Microsoft "
        header += str(platform.system()) + " " + str(platform.release()) + "\n"
        header += "Version " + str(platform.version()) + "\n"
        header += "CPU: " + str(cpuinfo.get_cpu_info()['brand']) + ", " + str(
            psutil.cpu_count(logical=False)) + " Core(s), " + str(
            psutil.cpu_count(logical=True)) + " Logical Processor(s)\n"
        header += "Total Physical Memory: " + str(get_size(psutil.virtual_memory().total))

        machine = os_statistics_pb2.MachineName()
        machine.name = header
        return machine

    def GetStatistics(self, request, context):
        def on_rpc_done():
            self.pid = None
            self.event.set()

        context.add_callback(on_rpc_done)

        self.event.set()

        statistics = os_statistics_pb2.ServerServiceStatistics()

        statistics.cpu.total_cpu_usage = self.statistics.total_cpu_usage
        statistics.cpu.cpu_usage_per_core.extend(self.statistics.cpu_usage_per_core)

        statistics.memory.total = self.memory_total
        statistics.memory.available = self.statistics.memory_available
        statistics.memory.used = self.statistics.memory_used
        statistics.memory.percentage = self.statistics.memory_percentage

        statistics.process_info.cpu_percent = self.statistics.process_info_cpu_percent
        statistics.process_info.rss = self.statistics.process_info_rss
        statistics.process_info.vms = self.statistics.process_info_vms
        statistics.process_info.uss = self.statistics.process_info_uss
        if platform == "linux" or platform == "linux2":
            statistics.process_info.pss = self.statistics.process_info_pss

        statistics.process_info.memory_percent_rss = self.statistics.process_info_memory_percent_rss
        statistics.process_info.memory_percent_vms = self.statistics.process_info_memory_percent_vms
        statistics.process_info.memory_percent_uss = self.statistics.process_info_memory_percent_uss
        if platform == "linux" or platform == "linux2":
            statistics.process_info.memory_percent_pss = self.statistics.process_info_memory_percent_pss

        return statistics


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    os_statistics_pb2_grpc.add_OSStatisticsServiceServicer_to_server(StatisticsService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
