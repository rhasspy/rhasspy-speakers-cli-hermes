"""Hermes MQTT service for Rhasspy audio output with external program."""
import argparse
import asyncio
import logging
import shlex

import paho.mqtt.client as mqtt
import rhasspyhermes.cli as hermes_cli

from . import SpeakersHermesMqtt

_LOGGER = logging.getLogger("rhasspyspeakers_cli_hermes")

# -----------------------------------------------------------------------------


def main():
    """Main method."""
    parser = argparse.ArgumentParser(prog="rhasspy-speakers-cli-hermes")
    parser.add_argument(
        "--play-command", required=True, help="Command to play WAV data from stdin"
    )
    parser.add_argument(
        "--list-command", help="Command to list available output devices"
    )

    hermes_cli.add_hermes_args(parser)
    args = parser.parse_args()

    hermes_cli.setup_logging(args)
    _LOGGER.debug(args)

    args.play_command = shlex.split(args.play_command)

    if args.list_command:
        args.list_command = shlex.split(args.list_command)

    # Listen for messages
    client = mqtt.Client()
    hermes = SpeakersHermesMqtt(
        client, args.play_command, list_command=args.list_command, site_ids=args.site_id
    )

    _LOGGER.debug("Connecting to %s:%s", args.host, args.port)
    hermes_cli.connect(client, args)
    client.loop_start()

    try:
        # Run event loop
        asyncio.run(hermes.handle_messages_async())
    except KeyboardInterrupt:
        pass
    finally:
        _LOGGER.debug("Shutting down")
        client.loop_stop()


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
