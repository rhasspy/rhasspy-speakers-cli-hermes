SHELL := bash

.PHONY: reformat check dist sdist install test deploy

all:

# -----------------------------------------------------------------------------
# Python
# -----------------------------------------------------------------------------

reformat:
	scripts/format-code.sh

check:
	scripts/check-code.sh

install:
	scripts/create-venv.sh

dist: sdist

sdist:
	python3 setup.py sdist

test:
	scripts/run-tests.sh

deploy:
	docker login --username rhasspy --password "$$DOCKER_PASSWORD"
	scripts/build-docker.sh
