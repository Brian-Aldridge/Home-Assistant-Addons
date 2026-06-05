#!/usr/bin/env bash
set -euo pipefail

echo "[bridge] starting Music Assistant SendSpin AirPlay Bridge"
exec python -m app.main
