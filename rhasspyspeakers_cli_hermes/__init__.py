"""Hermes MQTT server for Rhasspy audio output using external program"""
import audioop
import io
import json
import logging
import re
import subprocess
import typing
import wave

import wavchunk
from rhasspyhermes.audioserver import (
    AudioDevice,
    AudioDeviceMode,
    AudioDevices,
    AudioGetDevices,
    AudioPlayBytes,
    AudioPlayError,
    AudioPlayFinished,
    AudioSetVolume,
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
        volume: float = 1.0,
        site_ids: typing.Optional[typing.List[str]] = None,
    ):
        super().__init__("rhasspyspeakers_cli_hermes", client, site_ids=site_ids)

        self.subscribe(
            AudioPlayBytes,
            AudioGetDevices,
            AudioToggleOff,
            AudioToggleOn,
            AudioSetVolume,
        )

        self.play_command = play_command
        self.list_command = list_command
        self.volume = volume

        self.enabled = True

    # -------------------------------------------------------------------------

    async def handle_play(
        self,
        request_id: str,
        wav_bytes: bytes,
        site_id: str = "default",
        session_id: str = "",
    ) -> typing.AsyncIterable[
        typing.Union[typing.Tuple[AudioPlayFinished, TopicArgs], AudioPlayError]
    ]:
        """Play WAV using external program."""
        try:
            if self.enabled:
                _LOGGER.debug(self.play_command)

                # Check for volume in WAV INFO chunk
                wav_bytes = SpeakersHermesMqtt.maybe_change_volume(
                    wav_bytes, master_volume=self.volume
                )

                subprocess.run(self.play_command, input=wav_bytes, check=True)
            else:
                _LOGGER.debug("Not playing (audio disabled)")
        except Exception as e:
            _LOGGER.exception("handle_play")
            yield AudioPlayError(
                error=str(e), context=request_id, site_id=site_id, session_id=session_id
            )
        finally:
            yield (
                AudioPlayFinished(id=request_id, session_id=session_id),
                {"site_id": site_id},
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
                error=str(e), context=get_devices.id, site_id=get_devices.site_id
            )

        yield AudioDevices(
            devices=devices, id=get_devices.id, site_id=get_devices.site_id
        )

    # -------------------------------------------------------------------------

    async def on_message(
        self,
        message: Message,
        site_id: typing.Optional[str] = None,
        session_id: typing.Optional[str] = None,
        topic: typing.Optional[str] = None,
    ) -> GeneratorType:
        """Received message from MQTT broker."""
        if isinstance(message, AudioPlayBytes):
            assert site_id and topic, "Missing site_id or topic"
            request_id = AudioPlayBytes.get_request_id(topic)
            session_id = session_id or ""
            async for play_result in self.handle_play(
                request_id, message.wav_bytes, site_id=site_id, session_id=session_id
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
        elif isinstance(message, AudioSetVolume):
            old_volume = self.volume
            self.volume = message.volume
            _LOGGER.debug("Volume set to %s (was %s)", self.volume, old_volume)
        else:
            _LOGGER.warning("Unexpected message: %s", message)

    # -------------------------------------------------------------------------

    @staticmethod
    def maybe_change_volume(wav_bytes: bytes, master_volume: float = 1.0) -> bytes:
        """
        Look for an INFO chunk in WAV.
        If in contains a JSON object with a 'volume' property, scale amplitude
        by that factor.
        """
        try:
            with io.BytesIO(wav_bytes) as wav_in_io:
                info_data = wavchunk.get_chunk(wav_in_io)
                volume = master_volume

                if info_data:
                    # Interpret contents as JSON
                    info_obj = json.loads(info_data)
                    volume = max(0, float(info_obj.get("volume", 1.0))) * master_volume

                if volume != 1.0:
                    # Transform amplitude
                    wav_in_io.seek(0)

                    # Re-write WAV with adjusted volume
                    with io.BytesIO() as wav_out_io:
                        wav_out_file: wave.Wave_write = wave.open(wav_out_io, "wb")
                        wav_in_file: wave.Wave_read = wave.open(wav_in_io, "rb")

                        with wav_out_file:
                            with wav_in_file:
                                sample_width = wav_in_file.getsampwidth()

                                # Copy WAV details
                                wav_out_file.setframerate(wav_in_file.getframerate())
                                wav_out_file.setsampwidth(sample_width)
                                wav_out_file.setnchannels(wav_in_file.getnchannels())

                                # Adjust amplitude
                                wav_out_file.writeframes(
                                    audioop.mul(
                                        wav_in_file.readframes(
                                            wav_in_file.getnframes()
                                        ),
                                        sample_width,
                                        volume,
                                    )
                                )

                        wav_bytes = wav_out_io.getvalue()
                        _LOGGER.debug(
                            "Final volume is %s (master=%s)", volume, master_volume
                        )

        except Exception:
            _LOGGER.exception("maybe_change_volume")

        return wav_bytes
