"""Hermes MQTT server for Rhasspy audio output using external program"""
import json
import logging
import shlex
import subprocess
import typing

import attr
from rhasspyhermes.audioserver import AudioPlayBytes, AudioPlayFinished
from rhasspyhermes.base import Message

_LOGGER = logging.getLogger(__name__)


class SpeakersHermesMqtt:
    """Hermes MQTT server for Rhasspy audio output using external program."""

    def __init__(
        self,
        client,
        play_command: str,
        siteIds: typing.Optional[typing.List[str]] = None,
    ):
        self.client = client
        self.play_command: typing.List[str] = shlex.split(play_command)
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
            yield self.publish(AudioPlayFinished(id=requestId, sessionId=sessionId))

    # -------------------------------------------------------------------------

    def on_connect(self, client, userdata, flags, rc):
        """Connected to MQTT broker."""
        try:
            topics = []
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
