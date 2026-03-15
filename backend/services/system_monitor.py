from __future__ import annotations

import psutil


def get_system_stats() -> dict:
    """Return current CPU, RAM and disk usage."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    return {
        "cpu_percent": cpu,
        "ram_percent": mem.percent,
        "disk_percent": disk.percent,
        "ram_free_gb": round(mem.available / (1024**3), 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
    }
