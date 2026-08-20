import importlib

from so import config


def load_schema():
    return importlib.import_module(f"so.schemas.{config.SCHEMA_NAME}")
