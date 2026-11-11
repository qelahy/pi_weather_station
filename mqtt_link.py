"""Connect to your Pi broker. This lab uses unencrypted MQTT on port 1883."""

import getpass
import json
import os
import uuid

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:  # pragma: no cover - dependency is optional for static checks.
    mqtt = None
    _MQTT_IMPORT_ERROR = exc
else:
    _MQTT_IMPORT_ERROR = None


def make_client(config, suffix):
    if mqtt is None:
        raise RuntimeError("paho-mqtt is required for MQTT publishing") from _MQTT_IMPORT_ERROR

    username = config.get("mqtt_username", "")
    client_id = f"{username or 'anonymous'}-{suffix}-{uuid.uuid4().hex[:8]}"

    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
    except TypeError:
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

    # Leave mqtt_username empty for the first, anonymous connection test.
    # A separate MQTT password can be enabled after that test; never reuse eduroam credentials.
    if username:
        password = os.environ.get("MQTT_PASSWORD") or getpass.getpass(
            f"MQTT password for {username}: "
        )
        client.username_pw_set(username, password)

    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.max_queued_messages_set(32)
    client.max_inflight_messages_set(4)
    return client


class Publisher:
    def __init__(self, config):
        self.config = config
        self.base = f"weather/{config['station_id']}"
        self.client = make_client(config, "station")
        self.client.will_set(self.base + "/status", "offline", qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_connect_fail = self.on_connect_fail
        self.client.on_disconnect = self.on_disconnect
        self.client.connect_async(config["broker_host"], config["broker_port"], keepalive=30)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        is_failure = getattr(reason_code, "is_failure", False)
        if isinstance(reason_code, int):
            is_failure = reason_code != 0
        if is_failure:
            print("MQTT authentication/connection rejected:", reason_code)
            return
        print("MQTT connected to the Pi broker (not encrypted).")
        client.publish(self.base + "/status", "online", qos=1, retain=True)

    def on_connect_fail(self, client, userdata):
        print("MQTT unreachable; local collection continues.")

    def on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        print("MQTT disconnected; local collection is independent of the broker.")

    def publish(self, row):
        if not self.client.is_connected():
            return False
        result = self.client.publish(
            self.base + "/telemetry",
            json.dumps(row, allow_nan=False),
            qos=1,
            retain=True,
        )
        # Success means queued, NOT that the central database has committed the reading.
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def close(self):
        try:
            if self.client.is_connected():
                message = self.client.publish(
                    self.base + "/status", "offline", qos=1, retain=True
                )
                if message is not None:
                    message.wait_for_publish(timeout=2)
        finally:
            self.client.disconnect()
            self.client.loop_stop()