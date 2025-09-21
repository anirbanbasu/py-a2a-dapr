# py-a2a-dapr

A template repository for developing Dapr managed Agent2Agent (A2A) systems in Python.

- Install [`uv` package manager](https://docs.astral.sh/uv/getting-started/installation/).
- Install project dependencies by running `uv sync --all-groups`.
- Configure dapr to run [with docker](https://docs.dapr.io/operations/hosting/self-hosted/self-hosted-with-docker/).
- Run `dapr init` to initialise `daprd` and the containers.
- Start the Dapr actor service and the A2A endpoints by running `./start_dapr_multi.sh`. (This will send the dapr sidecar processes in the background.)
- Invoke the A2A agent using JSON-RPC by calling `uv run a2a-client`.
- Or, start the web app by running `uv run web-app` and then browse to http://localhost:7860.
- Stop the dapr sidecars by running `./stop_dapr_multi.sh`.
