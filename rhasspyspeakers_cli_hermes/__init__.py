"""Hermes MQTT server for Rhasspy audio output using external program"""
import json
import logging
import re
import subprocess
import typing

import attr
from rhasspyhermes.audioserver import (
    AudioDevice,
    AudioDeviceMode,
    AudioDevices,
    AudioGetDevices,
    AudioPlayBytes,
    AudioPlayFinished,
)
from rhasspyhermes.base import Message

_LOGGER = logging.getLogger("rhasspyspeakers_cli_hermes")

# -----------------------------------------------------------------------------


class SpeakersHermesMqtt:
    """Hermes MQTT server for Rhasspy audio output using external program."""

    def __init__(
        self,
        client,
        play_command: typing.List[str],
        list_command: typing.Optional[typing.List[str]] = None,
        siteIds: typing.Optional[typing.List[str]] = None,
    ):
        self.client = client
        self.play_command = play_command
        self.list_command = list_command
        self.siteIds = siteIds or []

    # -------------------------------------------------------------------------

    def handle_play(
        self, requestId: str, wav_bytes: bytes, sessionId: str = ""
    ) -> typing.Iterable[AudioPlayFinished]:
        """Play WAV using external program."""
        try:
            _LOGGER.debug(self.play_command)
            subprocess.run(self.play_command, input=wav_bytes, check=True)
        except Exception:
            _LOGGER.exception("handle_play")
        finally:
            yield AudioPlayFinished(id=requestId, sessionId=sessionId)

    def handle_get_devices(
        self, get_devices: AudioGetDevices
    ) -> typing.Optional[AudioDevices]:
        """Get available speakers."""
        if get_devices.modes and (AudioDeviceMode.OUTPUT not in get_devices.modes):
            return None

        devices: typing.List[AudioDevice] = []

        try:
            assert self.list_command, "List command is required to get devices"
            _LOGGER.debug(self.list_command)
            output = subprocess.check_output(
                self.list_command, universal_newlines=True
            ).splitlines()

            name, description = None, ""

            # Parse output of list command (assume like arecord -L)
            first_speaker = True
            for line in output:
                line = line.rstrip()
                if re.match(r"^\s", line):
                    description = line.strip()
                    if first_speaker:
                        description = description + "*"
                        first_speaker = False
                else:
                    if name is not None:
                        devices.append(
                            AudioDevice(
                                mode=AudioDeviceMode.OUTPUT,
                                id=name,
                                name=name,
                                description=description,
                            )
                        )

                    name = line.strip()

        except Exception:
            _LOGGER.exception("handle_get_devices")

        return AudioDevices(
            devices=devices, id=get_devices.id, siteId=get_devices.siteId
        )

    # -------------------------------------------------------------------------

    def on_connect(self, client, userdata, flags, rc):
        """Connected to MQTT broker."""
        try:
            topics = [AudioGetDevices.topic()]
            if self.siteIds:
                # Subscribe to specific siteIds
                for siteId in self.siteIds:
                    topics.append(AudioPlayBytes.topic(siteId=siteId, requestId="#"))
            else:
                # Subscribe to all siteIds
                topics.append(AudioPlayBytes.topic(siteId="+", requestId="#"))

            for topic in topics:
                self.client.subscribe(topic)
                _LOGGER.debug("Subscribed to %s", topic)
        except Exception:
            _LOGGER.exception("on_connect")

    def on_message(self, client, userdata, msg):
        """Received message from MQTT broker."""
        try:
            _LOGGER.debug("Received %s byte(s) on %s", len(msg.payload), msg.topic)

            if AudioPlayBytes.is_topic(msg.topic):
                siteId = AudioPlayBytes.get_siteId(msg.topic)
                requestId = AudioPlayBytes.get_requestId(msg.topic)
                wav_bytes = bytes(msg.payload)

                for message in self.handle_play(requestId, wav_bytes):
                    if isinstance(message, AudioPlayFinished):
                        self.publish(message, siteId=siteId)
            elif msg.topic == AudioGetDevices.topic():
                json_payload = json.loads(msg.payload)
                if self._check_siteId(json_payload):
                    result = self.handle_get_devices(
                        AudioGetDevices.from_dict(json_payload)
                    )
                    if result:
                        self.publish(result)
        except Exception:
            _LOGGER.exception("on_message")

    def publish(self, message: Message, **topic_args):
        """Publish a Hermes message to MQTT."""
        try:
            _LOGGER.debug("-> %s", message)
            topic = message.topic(**topic_args)
            payload = json.dumps(attr.asdict(message))
            _LOGGER.debug("Publishing %s char(s) to %s", len(payload), topic)
            self.client.publish(topic, payload)
        except Exception:
            _LOGGER.exception("on_message")

    # -------------------------------------------------------------------------

    def _check_siteId(self, json_payload: typing.Dict[str, typing.Any]) -> bool:
        if self.siteIds:
            return json_payload.get("siteId", "default") in self.siteIds

        # All sites
        return True
