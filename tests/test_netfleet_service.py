from __future__ import annotations

from types import SimpleNamespace

import netfleet_service


def test_netfleet_returns_unconfigured_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(
        netfleet_service,
        "settings",
        SimpleNamespace(
            netfleet_api_key=None,
            netfleet_base_url="https://api.netfleet.bg:8080",
            netfleet_timeout_seconds=5,
        ),
    )

    telemetry = netfleet_service.fetch_latest_gps_events()
    assert telemetry.configured is False
    assert telemetry.items == []


def test_netfleet_fetches_with_api_key_header_and_normalizes_payload(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"""
            [
              {
                "deviceId": 42,
                "plateNumber": " cb1234aa ",
                "latitude": 42.6977,
                "longitude": 23.3219,
                "speed": 0,
                "utcTime": "2024-04-29 14:48:05",
                "currentMileage": 12345.6
              }
            ]
            """

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["api_key"] = request.headers["Api-key"]
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        netfleet_service,
        "settings",
        SimpleNamespace(
            netfleet_api_key="secret-test-key",
            netfleet_base_url="https://api.netfleet.bg:8080",
            netfleet_timeout_seconds=7,
        ),
    )
    monkeypatch.setattr(netfleet_service.urllib.request, "urlopen", fake_urlopen)

    telemetry = netfleet_service.fetch_latest_gps_events()

    assert captured == {
        "url": "https://api.netfleet.bg:8080/api/company/latest-gps-events",
        "api_key": "secret-test-key",
        "timeout": 7,
    }
    assert telemetry.configured is True
    assert telemetry.items == [
        {
            "device_id": 42,
            "plate_number": "CB1234AA",
            "latitude": 42.6977,
            "longitude": 23.3219,
            "speed": 0,
            "azimuth": None,
            "altitude": None,
            "power_voltage": None,
            "satellites": None,
            "utc_time": "2024-04-29 14:48:05",
            "current_mileage": 12345.6,
            "current_work_hours": None,
        }
    ]


def test_netfleet_accepts_runtime_api_key_override(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"[]"

    def fake_urlopen(request, timeout):
        captured["api_key"] = request.headers["Api-key"]
        return FakeResponse()

    monkeypatch.setattr(
        netfleet_service,
        "settings",
        SimpleNamespace(
            netfleet_api_key=None,
            netfleet_base_url="https://api.netfleet.bg:8080",
            netfleet_timeout_seconds=5,
        ),
    )
    monkeypatch.setattr(netfleet_service.urllib.request, "urlopen", fake_urlopen)

    telemetry = netfleet_service.fetch_latest_gps_events(api_key="runtime-ui-key")

    assert telemetry.configured is True
    assert telemetry.items == []
    assert captured["api_key"] == "runtime-ui-key"
