#!/bin/bash
# Ensure any existing Dapr instances are stopped
dapr stop -f .
# Start Dapr with the specified configuration file
dapr run -f . &
