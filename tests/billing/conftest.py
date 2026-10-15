"""Fail closed if any billing test tries to perform an outbound request."""

from __future__ import annotations

import socket
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def deny_outbound_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("billing test attempted outbound network access")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)
