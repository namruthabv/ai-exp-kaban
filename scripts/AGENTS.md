# Local scripts

This folder contains start and stop scripts for macOS, Linux, and Windows.

- Scripts must work when invoked from any current directory.
- Start scripts build and launch the Docker Compose application in the background.
- Stop scripts remove the Compose containers and network without deleting unrelated Docker resources.
- Keep platform scripts explicit and short; do not add environment setup that belongs in Docker.
