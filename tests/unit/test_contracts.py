import pytest
from pydantic import ValidationError
from apps.api.app.domain.iot.contracts import (
    SensorTelemetryPayload, SensorStatus, OperationalAlert, TruckCommand
)

def test_valid_sensor_telemetry_payload():
    payload = SensorTelemetryPayload(
        event_id="EVT-100",
        sensor_id="SEN-01",
        bin_id="BIN-01",
        sim_time="2026-09-03T08:30:00-03:00",
        fill_pct=88.5,
        distance_cm=14.0,
        temperature_c=27.5,
        battery_pct=95.0,
        signal_quality=92,
        status=SensorStatus.ONLINE,
        lat=-15.79,
        lon=-47.88
    )
    assert payload.fill_pct == 88.5
    assert payload.status == SensorStatus.ONLINE

def test_invalid_negative_fill_pct_rejected():
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(
            event_id="EVT-101",
            sensor_id="SEN-01",
            bin_id="BIN-01",
            sim_time="2026-09-03T08:30:00-03:00",
            fill_pct=-5.0, # Inválido: ge=0.0
            distance_cm=14.0,
            temperature_c=27.5,
            battery_pct=95.0,
            signal_quality=92,
            lat=-15.79,
            lon=-47.88
        )

def test_truck_command_idempotency_structure():
    cmd = TruckCommand(
        command_id="CMD-9988A",
        correlation_id="CORR-123",
        truck_id="TR-01",
        action="ASSIGN_ROUTE",
        target_node="RODOVIARIA_PLANO",
        target_bin_id="BIN-02",
        issued_sim_time="2026-09-03T08:35:00-03:00"
    )
    assert cmd.command_id == "CMD-9988A"
    assert cmd.action == "ASSIGN_ROUTE"
