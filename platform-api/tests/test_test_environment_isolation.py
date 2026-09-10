"""Regression for the accidental business-Runtime connection during a local test."""

import socket

import pytest

from app.config import get_settings


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
@pytest.mark.parametrize(
    "address",
    [
        ("127.0.0.1", 8100),
        ("127.0.0.1", 8000),
        ("127.0.0.1", 4373),
        ("203.0.113.1", 443),
    ],
)
def test_business_and_external_network_are_blocked_before_socket_io(method, address):
    with socket.socket() as sock, pytest.raises(AssertionError, match="business service"):
        getattr(sock, method)(address)


def test_default_runtime_cannot_target_the_business_service():
    assert get_settings().runtime_base_url == "http://127.0.0.1:1"
