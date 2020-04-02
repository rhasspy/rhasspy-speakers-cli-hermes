"""Hermes MQTT server for Rhasspy audio output using external program"""
import logging
import re
import subprocess
import typing

from rhasspyhermes.audioserver import (
    AudioDevice,
    AudioDeviceMode,
    AudioDevices,
    AudioGetDevices,
    AudioPlayBytes,
    AudioPlayError,
    AudioPlayFinished,
    AudioToggleOff,
    AudioToggleOn,
)
from rhasspyhermes.base import Message
from rhasspyhermes.client import GeneratorType, HermesClient, TopicArgs

_LOGGER = logging.getLogger("rhasspyspeakers_cli_hermes")

# -----------------------------------------------------------------------------


class SpeakersHermesMqtt(HermesClient):
    """Hermes MQTT server for Rhasspy audio output using external program."""

    def __init__(
        self,
        client,
        play_command: typing.List[str],
        list_command: typing.Optional[typing.List[str]] = None,
        siteIds: typing.Optional[typing.List[str]] = None,
    ):
        super().__init__("rhasspyspeakers_cli_hermes", client, siteIds=siteIds)

        self.subscribe(AudioPlayBytes, AudioGetDevices, AudioToggleOff, AudioToggleOn)

        self.play_command = play_command
        self.list_command = list_command

        self.enabled = True

    # -------------------------------------------------------------------------

    async def handle_play(
        self,
        requestId: str,
        wav_bytes: bytes,
        siteId: str = "default",
        sessionId: str = "",
    ) -> typing.AsyncIterable[
        typing.Union[typing.Tuple[AudioPlayFinished, TopicArgs], AudioPlayError]
    ]:
        """Play WAV using external program."""
        try:
            if self.enabled:
                _LOGGER.debug(self.play_command)
                subprocess.run(self.play_command, input=wav_bytes, check=True)
            else:
                _LOGGER.debug("Not playing (audio disabled)")
        except Exception as e:
            _LOGGER.exception("handle_play")
            yield AudioPlayError(
                error=str(e), context=requestId, siteId=siteId, sessionId=sessionId
            )
        finally:
            yield (
                AudioPlayFinished(id=requestId, sessionId=sessionId),
                {"siteId": siteId},
            )

    async def handle_get_devices(
        self, get_devices: AudioGetDevices
    ) -> typing.AsyncIterable[typing.Union[AudioDevices, AudioPlayError]]:
        """Get available speakers."""
        if get_devices.modes and (AudioDeviceMode.OUTPUT not in get_devices.modes):
            return

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

        except Exception as e:
            _LOGGER.exception("handle_get_devices")
            yield AudioPlayError(
                error=str(e), context=get_devices.id, siteId=get_devices.siteId
            )

        yield AudioDevices(
            devices=devices, id=get_devices.id, siteId=get_devices.siteId
        )

    # -------------------------------------------------------------------------

    async def on_message(
        self,
        message: Message,
        siteId: typing.Optional[str] = None,
        sessionId: typing.Optional[str] = None,
        topic: typing.Optional[str] = None,
    ) -> GeneratorType:
        """Received message from MQTT broker."""
        if isinstance(message, AudioPlayBytes):
            assert siteId and topic, "Missing siteId or topic"
            requestId = AudioPlayBytes.get_requestId(topic)
            sessionId = sessionId or ""
            async for play_result in self.handle_play(
                requestId, message.wav_bytes, siteId=siteId, sessionId=sessionId
            ):
                yield play_result
        elif isinstance(message, AudioGetDevices):
            async for device_result in self.handle_get_devices(message):
                yield device_result
        elif isinstance(message, AudioToggleOff):
            self.enabled = False
            _LOGGER.debug("Disabled audio")
        elif isinstance(message, AudioToggleOn):
            self.enabled = True
            _LOGGER.debug("Enabled audio")
        else:
            _LOGGER.warning("Unexpected message: %s", message)
