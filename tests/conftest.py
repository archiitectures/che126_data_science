"""Use the real SDK when installed, a small parameter facade otherwise."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def offline_sdk(monkeypatch):
    try:
        __import__("google.cloud.bigquery")
    except ImportError:
        from che126_data_science.data_mining import patents

        def scalar(name, type_, value):
            return SimpleNamespace(name=name, type_=type_, value=value)

        def array(name, type_, values):
            return SimpleNamespace(name=name, type_=type_, values=values)

        sdk = SimpleNamespace(
            ScalarQueryParameter=scalar,
            ArrayQueryParameter=array,
            QueryJobConfig=lambda **kwargs: SimpleNamespace(**kwargs),
            Client=Mock(),
        )
        monkeypatch.setattr(patents, "_bigquery", lambda: sdk)
