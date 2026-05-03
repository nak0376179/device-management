"""Virtual network device that mirrors state via AWS IoT Device Shadow."""

from __future__ import annotations

import argparse
import json
import logging
import random
import signal
import threading
import time
from pathlib import Path
from typing import Any

from awscrt import io, mqtt
from awsiot import iotshadow, mqtt_connection_builder

logger = logging.getLogger("virtual_device")


class VirtualDevice:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.thing_name: str = config["thing_name"]
        self.client_id: str = config.get("client_id", self.thing_name)
        self.start_time = time.time()
        self.state_lock = threading.Lock()
        self.state = self._initial_state()
        self.mqtt_connection: mqtt.Connection | None = None
        self.shadow_client: iotshadow.IotShadowClient | None = None
        self._stop = threading.Event()

    def _initial_state(self) -> dict[str, Any]:
        return {
            "hostname": self.thing_name,
            "interfaces": {
                "eth0": {"enabled": True, "description": "WAN", "rx_bytes": 0, "tx_bytes": 0},
                "eth1": {"enabled": True, "description": "LAN1", "rx_bytes": 0, "tx_bytes": 0},
                "eth2": {"enabled": False, "description": "LAN2", "rx_bytes": 0, "tx_bytes": 0},
            },
            "system": {
                "uptime_sec": 0,
                "cpu_percent": round(random.uniform(2, 10), 1),
                "memory_percent": round(random.uniform(30, 60), 1),
            },
        }

    def connect(self) -> None:
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.config["endpoint"],
            cert_filepath=self.config["cert_path"],
            pri_key_filepath=self.config["key_path"],
            ca_filepath=self.config["ca_path"],
            client_bootstrap=client_bootstrap,
            client_id=self.client_id,
            clean_session=True,
            keep_alive_secs=30,
            on_connection_interrupted=self._on_interrupted,
            on_connection_resumed=self._on_resumed,
        )

        logger.info("Connecting to %s as %s ...", self.config["endpoint"], self.client_id)
        self.mqtt_connection.connect().result()
        logger.info("Connected.")

        self.shadow_client = iotshadow.IotShadowClient(self.mqtt_connection)
        self._subscribe_shadow()

        # 初回状態送信
        self._publish_reported_state()

    def _on_interrupted(self, connection, error, **_kwargs):
        logger.warning("Connection interrupted: %s", error)

    def _on_resumed(self, connection, return_code, session_present, **_kwargs):
        logger.info("Connection resumed: rc=%s session_present=%s", return_code, session_present)

    def _subscribe_shadow(self) -> None:
        assert self.shadow_client is not None

        self.shadow_client.subscribe_to_shadow_delta_updated_events(
            request=iotshadow.ShadowDeltaUpdatedSubscriptionRequest(thing_name=self.thing_name),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_delta_updated,
        )[0].result()

        self.shadow_client.subscribe_to_update_shadow_accepted(
            request=iotshadow.UpdateShadowSubscriptionRequest(thing_name=self.thing_name),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=lambda r: logger.debug("Shadow update accepted: version=%s", r.version),
        )[0].result()

        self.shadow_client.subscribe_to_update_shadow_rejected(
            request=iotshadow.UpdateShadowSubscriptionRequest(thing_name=self.thing_name),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=lambda e: logger.error("Shadow update rejected: %s", e.message),
        )[0].result()

        logger.info("Subscribed to shadow topics.")

    def _on_delta_updated(self, delta: iotshadow.ShadowDeltaUpdatedEvent) -> None:
        if not delta.state:
            return
        logger.info("Delta received: %s", json.dumps(delta.state))
        self._apply_desired(delta.state)
        self._publish_reported_state()

    def _apply_desired(self, desired: dict[str, Any]) -> None:
        with self.state_lock:
            _deep_merge(self.state, desired)

    def _publish_reported_state(self) -> None:
        if self._stop.is_set() or self.shadow_client is None:
            return

        with self.state_lock:
            self.state["system"]["uptime_sec"] = int(time.time() - self.start_time)
            reported = json.loads(json.dumps(self.state))

        request = iotshadow.UpdateShadowRequest(
            thing_name=self.thing_name,
            state=iotshadow.ShadowState(reported=reported),
        )

        # ★ 非同期（ここが重要）
        try:
            self.shadow_client.publish_update_shadow(
                request, mqtt.QoS.AT_LEAST_ONCE
            )
        except Exception as exc:
            logger.warning("Publish error: %s", exc)

    def run_telemetry_loop(self, interval: float) -> None:
        logger.info("Telemetry loop started (interval=%.1fs). Ctrl+C to stop.", interval)

        while not self._stop.is_set():
            if self._stop.wait(interval):
                break

            with self.state_lock:
                for iface in self.state["interfaces"].values():
                    if iface.get("enabled"):
                        iface["rx_bytes"] += random.randint(1_000, 100_000)
                        iface["tx_bytes"] += random.randint(1_000, 100_000)

                self.state["system"]["cpu_percent"] = round(random.uniform(2, 30), 1)
                self.state["system"]["memory_percent"] = round(random.uniform(30, 70), 1)

            if self._stop.is_set():
                break

            self._publish_reported_state()

        logger.info("Telemetry loop stopped.")

    def request_stop(self) -> None:
        self._stop.set()

    def stop(self) -> None:
        self._stop.set()

        # 少しだけ待って送信を流す（任意）
        time.sleep(0.2)

        conn, self.mqtt_connection = self.mqtt_connection, None
        if conn is not None:
            try:
                conn.disconnect().result(timeout=3)
                logger.info("Disconnected.")
            except Exception as exc:
                logger.warning("Disconnect error: %s", exc)


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def main() -> None:
    parser = argparse.ArgumentParser(description="Virtual network device for AWS IoT demo")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    config = json.loads(config_path.read_text())
    device = VirtualDevice(config)

    def _handle_signal(signum, _frame):
        logger.info("Signal %s received, stopping...", signum)
        device.request_stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        device.connect()
        device.run_telemetry_loop(args.interval)
    finally:
        device.stop()


if __name__ == "__main__":
    main()
