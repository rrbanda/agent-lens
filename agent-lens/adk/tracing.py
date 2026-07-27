"""MLflow tracing integration for Agent Lens ADK harness.

Enables TOOL and CHAT_MODEL spans when MLFLOW_TRACKING_URI is set.
Gracefully degrades if MLflow is unavailable or unreachable.
"""

from __future__ import annotations

import logging
import time
from os import getenv
from typing import Callable, Literal
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger("agent_lens.tracing")

_TRACING_ENABLED: bool = False


def _safe_uri(uri: str) -> str:
    parts = urlsplit(uri)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def _check_mlflow_health(tracking_uri: str, max_wait: int = 5) -> None:
    import requests

    url = f"{tracking_uri.rstrip('/')}/health"
    insecure = getenv("MLFLOW_TRACKING_INSECURE_TLS", "").lower() in ("true", "1", "yes")
    start = time.time()

    while True:
        remaining = max_wait - (time.time() - start)
        if remaining <= 0:
            raise RuntimeError(f"MLflow unreachable after {max_wait}s")
        try:
            resp = requests.get(url, timeout=min(5, remaining), verify=not insecure)
            if resp.status_code == 200:
                logger.info(f"MLflow health OK at {_safe_uri(url)}")
                return
            logger.warning(f"MLflow returned {resp.status_code} at {_safe_uri(url)}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"MLflow connect failed: {e}")
        time.sleep(1)


def wrap_func_with_mlflow_trace(
    func: Callable,
    span_type: Literal["tool", "agent"],
    name: str | None = None,
) -> Callable:
    if not _TRACING_ENABLED:
        return func
    import mlflow
    from mlflow.entities import SpanType

    st = SpanType.TOOL if span_type == "tool" else SpanType.AGENT
    return mlflow.trace(span_type=st, name=name)(func)


def enable_tracing() -> None:
    """Enable MLflow tracing if MLFLOW_TRACKING_URI is set.

    If the server is reachable, enables mlflow.litellm.autolog() for
    automatic CHAT_MODEL spans on all LiteLLM calls.
    """
    global _TRACING_ENABLED

    tracking_uri = getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        logger.info("MLFLOW_TRACKING_URI not set — tracing disabled")
        return

    try:
        import mlflow
        import mlflow.litellm
    except ModuleNotFoundError:
        logger.warning("mlflow not installed — tracing disabled")
        return

    try:
        timeout = int(getenv("MLFLOW_HEALTH_CHECK_TIMEOUT", "5"))
    except ValueError:
        timeout = 5

    try:
        _check_mlflow_health(tracking_uri, max_wait=timeout)
    except RuntimeError:
        logger.warning(f"MLflow unreachable at {_safe_uri(tracking_uri)} — continuing without tracing")
        return

    try:
        mlflow.set_tracking_uri(tracking_uri)
        experiment = getenv("MLFLOW_EXPERIMENT_NAME", "agent-lens-adk")
        mlflow.set_experiment(experiment)
        mlflow.config.enable_async_logging()
        mlflow.litellm.autolog()

        _TRACING_ENABLED = True
        logger.info(f"Tracing enabled → {_safe_uri(tracking_uri)}, experiment={experiment}")
    except Exception as e:
        logger.warning(f"Failed to configure tracing: {e}")
