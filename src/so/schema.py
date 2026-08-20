import importlib

from so import config

_module = importlib.import_module(f"so.schemas.{config.SCHEMA_NAME}")


def __getattr__(name):
    return getattr(_module, name)
