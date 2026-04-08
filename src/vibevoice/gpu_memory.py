"""
Best-effort PyTorch CUDA cache release for long-running API workers.
"""
from __future__ import annotations

import gc
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def cuda_device_index_from_string(device: str) -> Optional[int]:
    """
    Parse a device string (e.g. cuda, cuda:0) into a CUDA index, or None for CPU / non-CUDA.
    """
    d = (device or "").strip().lower()
    if not d or d == "cpu":
        return None
    if d == "cuda":
        return 0
    if d.startswith("cuda:"):
        try:
            return int(d.split(":", 1)[1])
        except ValueError:
            return 0
    return None


def cuda_free_bytes(device_index: int = 0) -> Optional[int]:
    """
    Return free bytes on the given CUDA device, or None if CUDA is not in use in this process.
    """
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    try:
        free, _total = torch.cuda.mem_get_info(device_index)
        return int(free)
    except Exception:
        logger.debug("cuda_free_bytes failed", exc_info=True)
        return None


def wait_for_cuda_memory(
    min_free_bytes: int,
    *,
    device_index: int = 0,
    timeout_seconds: float = 600.0,
    poll_interval_seconds: float = 2.0,
) -> bool:
    """
    Block until at least ``min_free_bytes`` are free on the CUDA device.

    If CUDA is unavailable, returns True immediately. If ``timeout_seconds`` is 0 or
    negative, waits indefinitely. Returns True when the threshold is met, False on timeout.
    """
    free = cuda_free_bytes(device_index)
    if free is None:
        return True
    if free >= min_free_bytes:
        return True

    deadline: Optional[float] = None
    if timeout_seconds > 0:
        deadline = time.monotonic() + timeout_seconds

    while True:
        free = cuda_free_bytes(device_index)
        if free is None:
            return True
        if free >= min_free_bytes:
            logger.info(
                "CUDA device %s ready: %.2f GiB free (required %.2f GiB)",
                device_index,
                free / (1024**3),
                min_free_bytes / (1024**3),
            )
            return True
        if deadline is not None and time.monotonic() >= deadline:
            logger.warning(
                "Timeout waiting for CUDA device %s: %.2f GiB free, need %.2f GiB",
                device_index,
                free / (1024**3),
                min_free_bytes / (1024**3),
            )
            return False
        logger.info(
            "Waiting for GPU memory on device %s: %.0f MiB free, need %.0f MiB (poll %.1fs)",
            device_index,
            free / (1024**2),
            min_free_bytes / (1024**2),
            poll_interval_seconds,
        )
        time.sleep(poll_interval_seconds)


def release_torch_cuda_memory() -> None:
    """Synchronize, collect Python objects, and empty CUDA allocator caches."""
    try:
        import torch
    except ImportError:
        gc.collect()
        return
    if not torch.cuda.is_available():
        gc.collect()
        return
    try:
        torch.cuda.synchronize()
    except Exception:
        logger.debug("cuda.synchronize during VRAM release", exc_info=True)
    gc.collect()
    torch.cuda.empty_cache()
    try:
        torch.cuda.ipc_collect()
    except Exception:
        pass
