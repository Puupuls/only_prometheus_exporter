import os
import platform
import re
import psutil
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from uvicorn import run

import nvsmi


def get_specs():
    INFO = {}

    INFO['hostname'] = os.uname()[1]
    INFO['kernel_version'] = os.uname()[2]
    INFO['os'] = os.uname()[0]

    with open('/etc/lsb-release', 'r') as f:
        for line in f.readlines():
            if 'DISTRIB_RELEASE' in line:
                INFO['os_version'] = line.split('=')[1].strip().strip('"')
            if 'DISTRIB_ID' in line:
                INFO['os_name'] = line.split('=')[1].strip().strip('"')

    INFO['os_architecture'] = platform.architecture()[0]

    with open('/proc/meminfo', 'r') as f:
        for line in f.readlines():
            if 'MemTotal' in line:
                INFO['ram_kb'] = line.split(':')[1].strip().split(' ')[0]
            if 'SwapTotal' in line:
                INFO['swap_kb'] = line.split(':')[1].strip().split(' ')[0]

    with open('/proc/cpuinfo') as f:
        for line in f.readlines():
            if 'vendor_id' in line:
                INFO['cpu_vendor'] = line.split(':')[1].strip()
            if 'model name' in line:
                INFO['cpu'] = line.split(':')[1].strip()
                INFO['cpu_model'] = line.split(':')[1].strip()
                if 'Intel' in INFO['cpu_vendor']:
                    INFO['cpu_model'] = re.sub(r'Intel\(R\) Core\(TM\) ', '', INFO['cpu_model'])
                    INFO['cpu_model'] = re.sub(r' CPU @ .*', '', INFO['cpu_model'])
                elif 'AMD' in INFO['cpu_vendor']:
                    INFO['cpu_model'] = re.sub(r'AMD ', '', INFO['cpu_model'])
                    INFO['cpu_model'] = re.sub(r' Processor', '', INFO['cpu_model'])
            if 'cpu cores' in line:
                INFO['cpu_cores'] = line.split(':')[1].strip()
    INFO['cpu_threads'] = os.cpu_count()

    return INFO


def get_gpu_prometheus_metrics():
    metrics = []
    if nvsmi.is_nvidia_smi_on_path():
        processes = nvsmi.get_gpu_processes()
        processes_by_gpu = {}
        for process in processes:
            processes_by_gpu.setdefault(process.gpu_uuid, []).append(process)
        for gpu in nvsmi.get_gpus():
            labels = (
                f"id=\"{gpu.id}\", "
                f"uuid=\"{gpu.uuid.replace('GPU-', '')}\", "
                f"name=\"{gpu.name}\" "
            )
            metrics.append(
                "nvidia_gpu_info{" + labels +
                f"driver=\"{gpu.driver}\", "
                f"mem_total={gpu.mem_total}"
                "} 1"
            )
            metrics.append(
                "nvidia_gpu_utilization{" + labels + "} "
                f"{gpu.gpu_util}"
            )
            metrics.append(
                "nvidia_gpu_memory_used{" + labels + "}"
                f" {gpu.mem_used}"
            )
            metrics.append(
                "nvidia_gpu_memory_free{" + labels + "} "
                f"{gpu.mem_free}"
            )
            metrics.append(
                "nvidia_gpu_memory_total{" + labels + "} "
                f"{gpu.mem_total}"
            )
            metrics.append(
                "nvidia_gpu_memory_utilization{" + labels + "} "
                f"{gpu.mem_util}"
            )
            metrics.append(
                "nvidia_gpu_temperature{" + labels + "} "
                f"{gpu.temperature}"
            )
            metrics.append(
                "nvidia_gpu_memory_temperature{" + labels + "} "
                f"{gpu.temperature_memory}"
            )
            metrics.append(
                "nvidia_gpu_fan_speed{" + labels + "} "
                f"{gpu.fan_speed}"
            )
            metrics.append(
                "nvidia_gpu_power_draw{" + labels + "} "
                f"{gpu.power_draw}"
            )
            metrics.append(
                "nvidia_gpu_power_limit{" + labels + "}"
                f" {gpu.power_limit}"
            )
            metrics.append(
                "nvidia_gpu_running_processes{" + labels + "}"
                f" {len(processes_by_gpu.get(gpu.uuid, []))}"
            )
            metrics.append(
                "nvidia_gpu_pstate{" + labels + "}"
                f" {gpu.pstate}"
            )
            metrics.append(
                "nvidia_gpu_clocks_throttle_reasons_gpu_idle{" + labels + "}"
                f" {gpu.clocks_throttle_reasons_gpu_idle}"
            )
            metrics.append(
                "nvidia_gpu_clocks_throttle_reasons_applications_clocks_setting{" + labels + "}"
                f" {gpu.clocks_throttle_reasons_applications_clocks_setting}"
            )
            metrics.append(
                "nvidia_gpu_clocks_throttle_reasons_sw_power_cap{" + labels + "}"
                f" {gpu.clocks_throttle_reasons_sw_power_cap}"
            )
            metrics.append(
                "nvidia_gpu_clocks_throttle_reasons_hw_thermal_slowdown{" + labels + "}"
                f" {gpu.clocks_throttle_reasons_hw_thermal_slowdown}"
            )
            metrics.append(
                "nvidia_gpu_clocks_throttle_reasons_hw_power_brake_slowdown{" + labels + "}"
                f" {gpu.clocks_throttle_reasons_hw_power_brake_slowdown}"
            )
            metrics.append(
                "nvidia_gpu_clocks_throttle_reasons_sw_thermal_slowdown{" + labels + "}"
                f" {gpu.clocks_throttle_reasons_sw_thermal_slowdown}"
            )
            metrics.append(
                "nvidia_gpu_clocks_current_graphics{" + labels + "}"
                f" {gpu.clocks_current_graphics}"
            )
            metrics.append(
                "nvidia_gpu_clocks_current_sm{" + labels + "}"
                f" {gpu.clocks_current_sm}"
            )
            metrics.append(
                "nvidia_gpu_clocks_current_memory{" + labels + "}"
                f" {gpu.clocks_current_memory}"
            )
            for process in processes_by_gpu.get(gpu.uuid, []):
                metrics.append(
                    "nvidia_gpu_process_info{" + labels +
                    f"pid=\"{process.pid}\", "
                    f"process_name=\"{process.name}\", "
                    f"used_memory={process.used_memory}"
                    "} 1"
                )

    return metrics


def get_disk_prometheus_metrics():
    metrics = []

    # Get disks/partitions connected to the system
    partitions = [partition for partition in psutil.disk_partitions()]
    # Filter junk
    partitions = [partition for partition in partitions if 'snap' not in partition.mountpoint]
    partitions = [partition for partition in partitions if 'docker' not in partition.mountpoint]
    partitions = [partition for partition in partitions if 'loop' not in partition.mountpoint]
    partitions = [partition for partition in partitions if 'boot' not in partition.mountpoint]
    partitions = [partition for partition in partitions if 'var/lib' not in partition.mountpoint]

    for partition in partitions:
        labels = (
            f"device=\"{partition.device}\", "
            f"mountpoint=\"{partition.mountpoint}\", "
            f"fstype=\"{partition.fstype}\""
        )
        usage = psutil.disk_usage(partition.mountpoint)
        metrics.append(
            "disk_usage{" + labels + "} "
            f"{usage.percent}"
        )
        metrics.append(
            "disk_total{" + labels + "} "
            f"{usage.total}"
        )
        metrics.append(
            "disk_used{" + labels + "} "
            f"{usage.used}"
        )
        metrics.append(
            "disk_free{" + labels + "} "
            f"{usage.free}"
        )

    return metrics


def get_cpu_prometheus_metrics():
    metrics = []

    return metrics


app = FastAPI(
    docs_url=None,
    redoc_url=None,
)


@app.get("/metrics")
def metrics():
    m1 = get_gpu_prometheus_metrics()
    m2 = get_disk_prometheus_metrics()
    m3 = get_cpu_prometheus_metrics()

    response = '\n'.join(m1 + m2 + m3)
    # return response as plain text encoding
    return PlainTextResponse(response)


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8754, reload=True)
