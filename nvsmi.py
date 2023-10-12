# Modified version of
# https://github.com/pmav99/nvsmi/blob/master/nvsmi.py (MIT licenced)
# To gather more metrics
import json
import os
import shlex
import shutil
import subprocess

__version__ = "0.4.2"


NVIDIA_SMI_GET_GPUS = ("nvidia-smi "
                       "--query-gpu="
                       "index,"
                       "uuid,"
                       "utilization.gpu,"
                       "memory.total,"
                       "memory.used,"
                       "memory.free,"
                       "driver_version,"
                       "name,"
                       "gpu_serial,"
                       "display_active,"
                       "display_mode,"
                       "temperature.gpu,"
                       "vbios_version,"
                       "fan.speed,"
                       "pstate,"
                       "clocks_throttle_reasons.gpu_idle,"
                       "clocks_throttle_reasons.applications_clocks_setting,"
                       "clocks_throttle_reasons.sw_power_cap,"
                       "clocks_throttle_reasons.hw_thermal_slowdown,"
                       "clocks_throttle_reasons.hw_power_brake_slowdown,"
                       "clocks_throttle_reasons.sw_thermal_slowdown,"
                       "temperature.memory,"
                       "power.draw,"
                       "power.limit,"
                       "enforced.power.limit,"
                       "clocks.current.graphics,"
                       "clocks.current.sm,"
                       "clocks.current.memory"
                       " --format=csv,noheader,nounits")
NVIDIA_SMI_GET_PROCS = "nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,gpu_name,used_memory --format=csv,noheader,nounits"


class GPU(object):
    def __init__(
            self,
            id,
            uuid,
            gpu_util,
            mem_total,
            mem_used,
            mem_free,
            driver,
            gpu_name,
            serial,
            display_mode,
            display_active,
            temperature,
            vbios_version,
            fan_speed,
            pstate,
            clocks_throttle_reasons_gpu_idle,
            clocks_throttle_reasons_applications_clocks_setting,
            clocks_throttle_reasons_sw_power_cap,
            clocks_throttle_reasons_hw_thermal_slowdown,
            clocks_throttle_reasons_hw_power_brake_slowdown,
            clocks_throttle_reasons_sw_thermal_slowdown,
            temperature_memory,
            power_draw,
            power_limit,
            enforced_power_limit,
            clocks_current_graphics,
            clocks_current_sm,
            clocks_current_memory
    ):
        self.id = id
        self.uuid = uuid
        self.gpu_util = gpu_util
        self.mem_util = float(mem_used) / float(mem_total) * 100
        self.mem_total = mem_total
        self.mem_used = mem_used
        self.mem_free = mem_free
        self.driver = driver
        self.name = gpu_name
        self.serial = serial
        self.display_mode = display_mode
        self.display_active = display_active
        self.temperature = temperature
        self.vbios_version = vbios_version
        self.fan_speed = fan_speed
        self.pstate = pstate
        self.clocks_throttle_reasons_gpu_idle = clocks_throttle_reasons_gpu_idle
        self.clocks_throttle_reasons_applications_clocks_setting = clocks_throttle_reasons_applications_clocks_setting
        self.clocks_throttle_reasons_sw_power_cap = clocks_throttle_reasons_sw_power_cap
        self.clocks_throttle_reasons_hw_thermal_slowdown = clocks_throttle_reasons_hw_thermal_slowdown
        self.clocks_throttle_reasons_hw_power_brake_slowdown = clocks_throttle_reasons_hw_power_brake_slowdown
        self.clocks_throttle_reasons_sw_thermal_slowdown = clocks_throttle_reasons_sw_thermal_slowdown
        self.temperature_memory = temperature_memory
        self.power_draw = power_draw
        self.power_limit = power_limit
        self.enforced_power_limit = enforced_power_limit
        self.clocks_current_graphics = clocks_current_graphics
        self.clocks_current_sm = clocks_current_sm
        self.clocks_current_memory = clocks_current_memory

    def __repr__(self):
        msg = "id: {id} | UUID: {uuid} | gpu_util: {gpu_util:5.1f}% | mem_util: {mem_util:5.1f}% | mem_free: {mem_free:7.1f}MB |  mem_total: {mem_total:7.1f}MB"
        msg = msg.format(**self.__dict__)
        return msg

    def to_json(self):
        return json.dumps(self.__dict__)


class GPUProcess(object):
    def __init__(self, pid, process_name, gpu_id, gpu_uuid, gpu_name, used_memory):
        self.pid = pid
        self.process_name = process_name
        self.gpu_id = gpu_id
        self.gpu_uuid = gpu_uuid
        self.gpu_name = gpu_name
        self.used_memory = used_memory

    def __repr__(self):
        msg = "pid: {pid} | gpu_id: {gpu_id} | gpu_uuid: {gpu_uuid} | gpu_name: {gpu_name} | used_memory: {used_memory:7.1f}MB"
        msg = msg.format(**self.__dict__)
        return msg

    def to_json(self):
        return json.dumps(self.__dict__)


def to_float_or_inf(value):
    try:
        number = float(value)
    except ValueError:
        number = float("nan")
    return number


def _get_gpu(line):
    values = line.split(", ")

    gpu = GPU(
        id=values[0],
        uuid=values[1],
        gpu_util=to_float_or_inf(values[2]),
        mem_total=to_float_or_inf(values[3]),
        mem_used=to_float_or_inf(values[4]),
        mem_free=to_float_or_inf(values[5]),
        driver=values[6],
        gpu_name=values[7],
        serial=values[8],
        display_mode=values[9],
        display_active=values[10],
        temperature=to_float_or_inf(values[11]),
        vbios_version=values[12],
        fan_speed=values[13],
        pstate=values[14],
        clocks_throttle_reasons_gpu_idle=values[15] == "Active",
        clocks_throttle_reasons_applications_clocks_setting=values[16] == "Active",
        clocks_throttle_reasons_sw_power_cap=values[17] == "Active",
        clocks_throttle_reasons_hw_thermal_slowdown=values[18] == "Active",
        clocks_throttle_reasons_hw_power_brake_slowdown=values[19] == "Active",
        clocks_throttle_reasons_sw_thermal_slowdown=values[20] == "Active",
        temperature_memory=to_float_or_inf(values[21]),
        power_draw=to_float_or_inf(values[22]),
        power_limit=to_float_or_inf(values[23]),
        enforced_power_limit=to_float_or_inf(values[24]),
        clocks_current_graphics=to_float_or_inf(values[25]),
        clocks_current_sm=to_float_or_inf(values[26]),
        clocks_current_memory=to_float_or_inf(values[27])
    )
    return gpu


def get_gpus() -> list[GPU]:
    output = subprocess.check_output(shlex.split(NVIDIA_SMI_GET_GPUS))
    lines = output.decode("utf-8").split(os.linesep)
    gpus = (_get_gpu(line) for line in lines if line.strip())
    return gpus


def _get_gpu_proc(line, gpu_uuid_to_id_map):
    values = line.split(", ")
    pid = int(values[0])
    process_name = values[1]
    gpu_uuid = values[2]
    gpu_name = values[3]
    used_memory = to_float_or_inf(values[4])
    gpu_id = gpu_uuid_to_id_map.get(gpu_uuid, -1)
    proc = GPUProcess(pid, process_name, gpu_id, gpu_uuid, gpu_name, used_memory)
    return proc


def get_gpu_processes():
    gpu_uuid_to_id_map = {gpu.uuid: gpu.id for gpu in get_gpus()}
    output = subprocess.check_output(shlex.split(NVIDIA_SMI_GET_PROCS))
    lines = output.decode("utf-8").split(os.linesep)
    processes = [
        _get_gpu_proc(line, gpu_uuid_to_id_map) for line in lines if line.strip()
    ]
    return processes


def is_nvidia_smi_on_path():
    return shutil.which("nvidia-smi")

