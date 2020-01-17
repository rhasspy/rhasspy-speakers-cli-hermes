# Rhasspy Speakers Hermes MQTT Service

[![Continous Integration](https://github.com/rhasspy/rhasspy-speakers-cli-hermes/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-speakers-cli-hermes/actions)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-speakers-cli-hermes.svg)](https://github.com/rhasspy/rhasspy-speakers-cli-hermes/blob/master/LICENSE)

Implements `hermes/audioServer` output functionality from [Hermes protocol](https://docs.snips.ai/reference/hermes) using an external program like `aplay`.

## Running With Docker

```bash
docker run -it rhasspy/rhasspy-speakers-cli-hermes:<VERSION> <ARGS>
```

## Building From Source

Clone the repository and create the virtual environment:

```bash
git clone https://github.com/rhasspy/rhasspy-speakers-cli-hermes.git
cd rhasspy-speakers-cli-hermes
make venv
```

Run the `bin/rhasspy-speakers-cli-hermes` script to access the command-line interface:

```bash
bin/rhasspy-speakers-cli-hermes --help
```

## Building the Debian Package

Follow the instructions to build from source, then run:

```bash
source .venv/bin/activate
make debian
```

If successful, you'll find a `.deb` file in the `dist` directory that can be installed with `apt`.

## Building the Docker Image

Follow the instructions to build from source, then run:

```bash
source .venv/bin/activate
make docker
```

This will create a Docker image tagged `rhasspy/rhasspy-speakers-cli-hermes:<VERSION>` where `VERSION` comes from the file of the same name in the source root directory.

NOTE: If you add things to the Docker image, make sure to whitelist them in `.dockerignore`.

## Command-Line Options

```
usage: rhasspy-speakers-cli-hermes [-h] --play-command PLAY_COMMAND
                                   [--host HOST] [--port PORT]
                                   [--siteId SITEID] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --play-command PLAY_COMMAND
                        Command to play WAV data from stdin
  --host HOST           MQTT host (default: localhost)
  --port PORT           MQTT port (default: 1883)
  --siteId SITEID       Hermes siteId(s) to listen for (default: all)
  --debug               Print DEBUG messages to the console
```
