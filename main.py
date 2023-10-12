import os
import platform
import re
from datetime import datetime
import psutil
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from uvicorn import run
from cpuinfo import cpu
import nvsmi
try:
    from screenutils import list_screens
except ImportError:
    print("screenutils not installed")
    def list_screens():
        return []


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
                f"mem_total=\"{gpu.mem_total}\""
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
                    f"process_name=\"{process.process_name}\", "
                    f"used_memory=\"{process.used_memory}\""
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

    processors = set([i['physical id'] for i in cpu.info])
    cores = len(set([i['core id'] for i in cpu.info]))
    threads = len(set([i['processor'] for i in cpu.info]))

    metrics.append(
        "cpu_info{"
        f"processors=\"{len(processors)}\", "
        f"cores=\"{cores}\", "
        f"threads=\"{threads}\" "
        "} 1"
    )

    for processor in processors:
        processor_threads_list = [i for i in cpu.info if i['physical id'] == processor]
        processor_cores = len(set([i['core id'] for i in processor_threads_list]))
        processor_threads = len(set([i['processor'] for i in processor_threads_list]))

        metrics.append(
            "cpu_processor_info{"
            f"vendor=\"{processor_threads_list[0]['vendor_id']}\", "
            f"model=\"{processor_threads_list[0]['model name']}\", "
            f"processor=\"{processor}\", "
            f"cores=\"{processor_cores}\", "
            f"threads=\"{processor_threads}\" "
            "} 1"
        )

    for core in cpu.info:
        metrics.append(
            "cpu_thread_info{"
            f"vendor=\"{core['vendor_id']}\", "
            f"model=\"{core['model name']}\", "
            f"physical_id=\"{core['physical id']}\", "
            f"core_id=\"{core['core id']}\", "
            f"processor_id=\"{core['processor']}\", "
            f"apic_id=\"{core['apicid']}\" "
            "} 1"
        )

    metrics.append(
        "cpu_frequency{"
        f"min=\"{psutil.cpu_freq().min*1000*1000}\", "
        f"max=\"{psutil.cpu_freq().max*1000*1000}\""
        "} "
        f"{psutil.cpu_freq().current*1000*1000}"
    )

    cpu_percents = psutil.cpu_percent(percpu=True)
    cpu_times = psutil.cpu_times(percpu=True)
    for idx, thread in enumerate(cpu_percents):
        metrics.append(
            "cpu_utilization{"
            f"thread=\"{idx}\""
            "} "
            f"{thread}"
        )
    for idx, thread in enumerate(cpu_times):
        for key, value in thread._asdict().items():
            metrics.append(
                "cpu_times{"
                f"thread=\"{idx}\", "
                f"mode=\"{key}\""
                "} "
                f"{value}"
            )
    temps = psutil.sensors_temperatures()
    if 'coretemp' in temps:
        for sensor in temps['coretemp']:
            metrics.append(
                "cpu_temperature{"
                f"label=\"{sensor.label}\", "
                f"high=\"{sensor.high}\", "
                f"critical=\"{sensor.critical}\" "
                "} "
                f"{sensor.current}"
            )
            metrics.append(
                "cpu_temperature_high{"
                f"label=\"{sensor.label}\""
                "} "
                f"{sensor.high}"
            )
            metrics.append(
                "cpu_temperature_critical{"
                f"label=\"{sensor.label}\""
                "} "
                f"{sensor.critical}"
            )
    fans = psutil.sensors_fans()
    for sensor_cat in fans.items():
        for sensor in sensor_cat[1]:
            metrics.append(
                "fan_speed{"
                f"category=\"{sensor_cat[0]}\", "
                f"label=\"{sensor.label}\""
                "} "
                f"{sensor.current}"
            )
    metrics.append(
        "process_count "
        f"{len(psutil.pids())}"
    )

    return metrics


def get_host_prometheus_metrics():
    metrics = []

    os_version = 'Unknown'
    os_name = 'Unknown'
    with open('/etc/lsb-release', 'r') as f:
        for line in f.readlines():
            if 'DISTRIB_RELEASE' in line:
                os_version = line.split('=')[1].strip().strip('"')
            if 'DISTRIB_ID' in line:
                os_name = line.split('=')[1].strip().strip('"')

    metrics.append(
        "host_info{"
        f"hostname=\"{os.uname()[1]}\", "
        f"machine=\"{platform.machine()}\", "
        f"os=\"{platform.system()}\", "
        f"os_release=\"{platform.release()}\", "
        f"os_name=\"{os_name}\", "
        f"os_version=\"{os_version}\", "
        f"os_architecture=\"{platform.architecture()[0]}\" "
        "} 1"
    )

    metrics.append(
        "host_boot_time "
        f"{psutil.boot_time()}"
    )
    metrics.append(
        "host_uptime "
        f"{datetime.now().timestamp() - psutil.boot_time()}"
    )

    return metrics


def get_memory_prometheus_metrics():
    metrics = []

    metrics.append(
        "memory_ram_total"
        f" {psutil.virtual_memory().total}"
    )
    metrics.append(
        "memory_ram_used"
        f" {psutil.virtual_memory().used}"
    )
    metrics.append(
        "memory_ram_free"
        f" {psutil.virtual_memory().free}"
    )
    metrics.append(
        "memory_ram_available"
        f" {psutil.virtual_memory().available}"
    )
    metrics.append(
        "memory_ram_used_percent"
        f" {psutil.virtual_memory().percent}"
    )
    metrics.append(
        "memory_swap_total"
        f" {psutil.swap_memory().total}"
    )
    metrics.append(
        "memory_swap_used"
        f" {psutil.swap_memory().used}"
    )
    metrics.append(
        "memory_swap_free"
        f" {psutil.swap_memory().free}"
    )
    metrics.append(
        "memory_swap_used_percent"
        f" {psutil.swap_memory().percent}"
    )

    return metrics


def get_screen_prometheus_metrics():
    metrics = []

    screens = list_screens()
    metrics.append(
        "screen_count "
        f"{len(screens)}"
    )
    for screen in screens:
        command = (f"ps u -p $(ps -el | grep $(ps -el | grep {screen.id} | "
                   "grep bash | awk '{print $4}') | grep -v bash | awk '{print $4}')")
        output = os.popen(command).read()
        if output:
            output = output.split('\n')[-2]
            output = " ".join(output.split()[10:])

        metrics.append(
            "screen_info{"
            f"pid=\"{screen.id}\", "
            f"open_time=\"{datetime.strptime(screen._date, '%m/%d/%Y %I:%M:%S %p').timestamp()}\", "
            f"status=\"{screen.status}\", "
            f"name=\"{screen.name}\", "
            f"command=\"{output}\" "
            "} 1"
        )

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
    m4 = get_host_prometheus_metrics()
    m5 = get_memory_prometheus_metrics()
    m6 = get_screen_prometheus_metrics()

    response = '\n'.join(sorted(m1 + m2 + m3 + m4 + m5 + m6))
    # return response as plain text encoding
    return PlainTextResponse(response)


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8754)
