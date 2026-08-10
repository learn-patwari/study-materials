import functools
import logging

logger = logging.getLogger(__name__)


class AgentError(Exception):
    pass


class ConfigError(Exception):
    pass


def graceful(agent_name: str):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                msg = f"{agent_name} unavailable: {exc}"
                logger.warning(msg)
                return {"error": msg}
        return wrapper
    return decorator
