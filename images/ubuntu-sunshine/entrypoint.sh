#!/bin/bash
set -e

# Create runtime directory
mkdir -p /tmp/runtime-gamer/pulse

# Start virtual display
Xvfb :0 -screen 0 1920x1080x24 &

# Start PulseAudio
pulseaudio --start --exit-idle-time=-1

# Wait for X server to be ready
sleep 2

# Verify NVENC is available
echo "Verifying NVENC encoding support..."
if ! ffmpeg -encoders 2>/dev/null | grep -q nvenc; then
    echo "ERROR: NVENC encoding not available"
    exit 1
fi

echo "NVENC verification passed"

# Start Sunshine streaming server
echo "Starting Sunshine streaming server..."
sunshine &

# Wait for Sunshine to start
sleep 5

# Verify Sunshine is running
if ! curl -f http://localhost:47990/api/config >/dev/null 2>&1; then
    echo "ERROR: Sunshine failed to start"
    exit 1
fi

echo "Sunshine started successfully"
echo "Gaming session ready on port 47984 (TCP) and 47989 (UDP)"

# Keep container running
tail -f /dev/null