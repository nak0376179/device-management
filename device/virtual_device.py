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

from command_runner import fetch_and_execute

logger = logging.getLogger("virtual_device")


class VirtualDevice:
    def __init__(self, config: dict[str, Any], config_path: Path | None = None):
        self.config = config
        self._config_path = config_path
        self.thing_name: str = config["thing_name"]
        self.client_id: str = config.get("client_id", self.thing_name)
        self.backend_url: str = config.get("backend_url", "http://localhost:9001")
        self.api_key: str = config.get("api_key", "")
        self.start_time = time.time()
        self.state_lock = threading.Lock()
        self.state = self._initial_state()
        self.mqtt_connection: mqtt.Connection | None = None
        self.shadow_client: iotshadow.IotShadowClient | None = None
        self._stop = threading.Event()
        self._cmd_lock = threading.Lock()

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

        lwt_payload = json.dumps(
            {"state": {"reported": {"connected": False}}}
        ).encode()

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
            will=mqtt.Will(
                topic=f"$aws/things/{self.thing_name}/shadow/update",
                payload=lwt_payload,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                retain=False,
            ),
        )

        logger.info("Connecting to %s as %s ...", self.config["endpoint"], self.client_id)
        self.mqtt_connection.connect().result()
        logger.info("Connected.")

        self.shadow_client = iotshadow.IotShadowClient(self.mqtt_connection)
        self._subscribe_shadow()
        self._subscribe_commands()
        self._publish_connected(True)

    def _on_interrupted(self, connection, error, **_kwargs):
        logger.warning("Connection interrupted: %s", error)

    def _on_resumed(self, connection, return_code, session_present, **_kwargs):
        logger.info("Connection resumed: rc=%s session_present=%s", return_code, session_present)
        self._publish_connected(True)

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

    def _subscribe_commands(self) -> None:
        assert self.mqtt_connection is not None
        topic = f"cmd/notify/{self.thing_name}"
        subscribe_future, _ = self.mqtt_connection.subscribe(
            topic=topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_command_notify,
        )
        subscribe_future.result()
        logger.info("Subscribed to command topic: %s", topic)

    def _on_command_notify(self, topic, payload, **_kwargs):
        try:
            data = json.loads(payload)
            task_id = data.get("task_id")
        except Exception:
            logger.warning("Invalid command notification payload: %r", payload)
            return

        if not task_id:
            return

        api_key = self.api_key
        if not api_key and self._config_path is not None:
            try:
                fresh = json.loads(self._config_path.read_text())
                api_key = fresh.get("api_key", "")
                if api_key:
                    self.api_key = api_key
                    self.backend_url = fresh.get("backend_url", self.backend_url)
            except Exception:
                pass

        if not api_key:
            logger.warning("api_key not configured; ignoring task %s", task_id)
            return

        if not self._cmd_lock.acquire(blocking=False):
            logger.warning("Task %s ignored: another command is running", task_id)
            return

        def _run():
            try:
                fetch_and_execute(task_id, self.backend_url, api_key)
            finally:
                self._cmd_lock.release()

        threading.Thread(target=_run, daemon=True).start()

    def _on_delta_updated(self, delta: iotshadow.ShadowDeltaUpdatedEvent) -> None:
        if not delta.state:
            return
        logger.info("Delta received: %s", json.dumps(delta.state))
        self._apply_desired(delta.state)
        self._publish_reported_state()

    def _apply_desired(self, desired: dict[str, Any]) -> None:
        with self.state_lock:
            _deep_merge(self.state, desired)

    def _publish_connected(self, connected: bool) -> None:
        self._publish_reported_state(extra={"connected": connected})

    def _publish_reported_state(self, extra: dict[str, Any] | None = None) -> None:
        if self._stop.is_set() or self.shadow_client is None or self.mqtt_connection is None:
            return
        with self.state_lock:
            self.state["system"]["uptime_sec"] = int(time.time() - self.start_time)
            reported = json.loads(json.dumps(self.state))
        if extra:
            reported.update(extra)
        request = iotshadow.UpdateShadowRequest(
            thing_name=self.thing_name,
            state=iotshadow.ShadowState(reported=reported),
        )
        try:
            self.shadow_client.publish_update_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
        except Exception as exc:
            logger.warning("Publish error: %s", exc)

    def wait_until_stop(self) -> None:
        logger.info("Waiting for cloud commands. Ctrl+C to stop.")
        self._stop.wait()
        logger.info("Stop requested.")

    def request_stop(self) -> None:
        self._stop.set()

    def stop(self) -> None:
        self._stop.set()
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
    device = VirtualDevice(config, config_path=config_path)

    def _handle_signal(signum, _frame):
        logger.info("Signal %s received, stopping...", signum)
        device.request_stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        device.connect()
        device.wait_until_stop()
    finally:
        device.stop()


if __name__ == "__main__":
    main()
