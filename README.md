# Rhasspy Speakers Hermes MQTT Service

[![Continous Integration](https://github.com/rhasspy/rhasspy-speakers-cli-hermes/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-speakers-cli-hermes/actions)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-speakers-cli-hermes.svg)](https://github.com/rhasspy/rhasspy-speakers-cli-hermes/blob/master/LICENSE)

Implements `hermes/audioServer` output functionality from [Hermes protocol](https://docs.snips.ai/reference/hermes) using an external program like `aplay`.

## Requirements

* Python 3.7

## Installation

```bash
$ git clone https://github.com/rhasspy/rhasspy-speakers-cli-hermes
$ cd rhasspy-speakers-cli-hermes
$ ./configure
$ make
$ make install
```

## Running

```bash
$ bin/rhasspy-speakers-cli-hermes <ARGS>
```

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
