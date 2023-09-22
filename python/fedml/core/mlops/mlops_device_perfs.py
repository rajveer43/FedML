import json
import logging
import os
import time
import traceback
import uuid

import multiprocess as multiprocessing
import psutil

from fedml.computing.scheduler.comm_utils import sys_utils
from .system_stats import SysStats

from ...core.distributed.communication.mqtt.mqtt_manager import MqttManager
from .mlops_utils import MLOpsUtils


class MLOpsDevicePerfStats(object):
    """
    Class for reporting device performance statistics to MLOps.

    This class handles the reporting of device performance statistics to MLOps using MQTT.
    """

    def __init__(self):
        self.device_realtime_stats_process = None
        self.device_realtime_stats_event = None
        self.args = None
        self.device_id = None
        self.run_id = None
        self.edge_id = None

    def report_device_realtime_stats(self, sys_args):
        """
        Report device real-time statistics to MLOps.

        Args:
            sys_args: The system arguments passed to the device.

        This method sets up and starts a process to report real-time device statistics to MLOps.

        Returns:
            None
        """

        self.setup_realtime_stats_process(sys_args)

    def stop_device_realtime_stats(self):
        """
        Stop reporting device real-time statistics.

        This method sets the event to stop reporting device real-time statistics.

        Returns:
            None
        """
        if self.device_realtime_stats_event is not None:
            self.device_realtime_stats_event.set()

    def should_stop_device_realtime_stats(self):
        """
        Check if reporting of device real-time statistics should stop.

        Returns:
            bool: True if reporting should stop, False otherwise.
        """
        if self.device_realtime_stats_event is not None and self.device_realtime_stats_event.is_set():
            return True

        return False

    def setup_realtime_stats_process(self, sys_args):
        """
        Set up the process for reporting real-time device statistics.

        Args:
            sys_args: The system arguments passed to the device.

        This method sets up the process for reporting real-time device statistics to MLOps.

        Returns:
            None
        """
        perf_stats = MLOpsDevicePerfStats()
        perf_stats.args = sys_args
        perf_stats.edge_id = getattr(sys_args, "edge_id", None)
        perf_stats.edge_id = getattr(
            sys_args, "client_id", None) if perf_stats.edge_id is None else perf_stats.edge_id
        perf_stats.edge_id = 0 if perf_stats.edge_id is None else perf_stats.edge_id
        perf_stats.device_id = getattr(sys_args, "device_id", 0)
        perf_stats.run_id = getattr(sys_args, "run_id", 0)
        if self.device_realtime_stats_event is None:
            self.device_realtime_stats_event = multiprocessing.Event()
        self.device_realtime_stats_event.clear()
        perf_stats.device_realtime_stats_event = self.device_realtime_stats_event

        self.device_realtime_stats_process = multiprocessing.Process(
            target=perf_stats.report_device_realtime_stats_entry,
            args=(self.device_realtime_stats_event,))
        self.device_realtime_stats_process.start()

    def report_device_realtime_stats_entry(self, sys_event):
        """
        Entry point for reporting real-time device statistics.

        Args:
            sys_event: The system event used to control reporting.

        This method is the entry point for reporting real-time device statistics to MLOps.

        Returns:
            None
        """
        self.device_realtime_stats_event = sys_event
        mqtt_mgr = MqttManager(
            self.args.mqtt_config_path["BROKER_HOST"],
            self.args.mqtt_config_path["BROKER_PORT"],
            self.args.mqtt_config_path["MQTT_USER"],
            self.args.mqtt_config_path["MQTT_PWD"],
            180,
            "FedML_Metrics_DevicePerf_{}_{}_{}".format(
                str(self.args.device_id), str(self.edge_id), str(uuid.uuid4()))
        )
        mqtt_mgr.connect()
        mqtt_mgr.loop_start()

        parent_pid = psutil.Process(os.getpid()).ppid()
        sys_stats_obj = SysStats(process_id=parent_pid)

        # Notify MLOps with system information.
        while not self.should_stop_device_realtime_stats():
            try:
                MLOpsDevicePerfStats.report_gpu_device_info(
                    self.edge_id, mqtt_mgr=mqtt_mgr)
            except Exception as e:
                logging.debug("exception when reporting device pref: {}.".format(
                    traceback.format_exc()))
                pass

            time.sleep(10)

        logging.info("Device metrics process is about to exit.")
        mqtt_mgr.loop_stop()
        mqtt_mgr.disconnect()

    @staticmethod
    def report_gpu_device_info(edge_id, mqtt_mgr=None):
        """
        Report GPU device information to MLOps.

        Args:
            edge_id: The ID of the edge device.
            mqtt_mgr: The MQTT manager for communication.

        This method reports GPU device information to MLOps using MQTT.

        Returns:
            None
        """
        total_mem, free_mem, total_disk_size, free_disk_size, cup_utilization, cpu_cores, gpu_cores_total, \
            gpu_cores_available, sent_bytes, recv_bytes, gpu_available_ids = sys_utils.get_sys_realtime_stats()

        topic_name = "ml_client/mlops/gpu_device_info"
        artifact_info_json = {
            "edgeId": edge_id,
            "memoryTotal": round(total_mem * MLOpsUtils.BYTES_TO_GB, 2),
            "memoryAvailable": round(free_mem * MLOpsUtils.BYTES_TO_GB, 2),
            "diskSpaceTotal": round(total_disk_size * MLOpsUtils.BYTES_TO_GB, 2),
            "diskSpaceAvailable": round(free_disk_size * MLOpsUtils.BYTES_TO_GB, 2),
            "cpuUtilization": round(cup_utilization, 2),
            "cpuCores": cpu_cores,
            "gpuCoresTotal": gpu_cores_total,
            "gpuCoresAvailable": gpu_cores_available,
            "gpu_available_ids": gpu_available_ids,
            "networkTraffic": sent_bytes + recv_bytes,
            "updateTime": int(MLOpsUtils.get_ntp_time())
        }
        message_json = json.dumps(artifact_info_json)
        if mqtt_mgr is not None:
            mqtt_mgr.send_message_json(topic_name, message_json)
