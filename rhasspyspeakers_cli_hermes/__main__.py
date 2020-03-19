"""Hermes MQTT service for Rhasspy audio output with external program."""
import argparse
import asyncio
import logging
import shlex

import paho.mqtt.client as mqtt

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
    parser.add_argument(
        "--host", default="localhost", help="MQTT host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=1883, help="MQTT port (default: 1883)"
    )
    parser.add_argument(
        "--siteId",
        action="append",
        help="Hermes siteId(s) to listen for (default: all)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to the console"
    )
    parser.add_argument(
        "--log-format",
        default="[%(levelname)s:%(asctime)s] %(name)s: %(message)s",
        help="Python logger format",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=args.log_format)
    else:
        logging.basicConfig(level=logging.INFO, format=args.log_format)

    _LOGGER.debug(args)

    try:
        args.play_command = shlex.split(args.play_command)

        if args.list_command:
            args.list_command = shlex.split(args.list_command)

        loop = asyncio.get_event_loop()

        # Listen for messages
        client = mqtt.Client()
        hermes = SpeakersHermesMqtt(
            client,
            args.play_command,
            list_command=args.list_command,
            siteIds=args.siteId,
            loop=loop,
        )

        _LOGGER.debug("Connecting to %s:%s", args.host, args.port)
        client.connect(args.host, args.port)
        client.loop_start()

        # Run event loop
        hermes.loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _LOGGER.debug("Shutting down")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
