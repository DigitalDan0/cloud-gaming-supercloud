FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies and NVIDIA container runtime
RUN apt-get update && apt-get install -y \
    wget curl gnupg software-properties-common apt-transport-https ca-certificates \
    sudo xvfb pulseaudio xfce4 xfce4-terminal lutris mesa-utils \
    libnvidia-encode-535 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install NVIDIA drivers (container runtime provides GPU access)
RUN wget -O- https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | gpg --dearmor > /usr/share/keyrings/nvidia-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/nvidia-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /" > /etc/apt/sources.list.d/nvidia-cuda.list \
    && apt-get update && apt-get install -y nvidia-driver-535 cuda-toolkit-12-2 \
    && rm -rf /var/lib/apt/lists/*

# Install Sunshine streaming server
RUN wget -O sunshine.deb https://github.com/LizardByte/Sunshine/releases/download/v0.20.0/sunshine-ubuntu-22.04-amd64.deb \
    && apt-get update && apt-get install -y ./sunshine.deb \
    && rm sunshine.deb && rm -rf /var/lib/apt/lists/*

# Install Steam and SteamCMD
RUN dpkg --add-architecture i386 \
    && wget -O- https://repo.steampowered.com/steam/archive/precise/steam.gpg | gpg --dearmor > /usr/share/keyrings/steam-archive-keyring.gpg \
    && echo "deb [arch=amd64,i386 signed-by=/usr/share/keyrings/steam-archive-keyring.gpg] https://repo.steampowered.com/steam/ stable steam" > /etc/apt/sources.list.d/steam.list \
    && apt-get update && apt-get install -y steam-launcher steamcmd lib32gcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Install Proton GE for Windows game compatibility
RUN mkdir -p /opt/proton \
    && wget -O proton.tar.gz https://github.com/GloriousEggroll/proton-ge-custom/releases/download/GE-Proton8-26/GE-Proton8-26.tar.gz \
    && tar -xzf proton.tar.gz -C /opt/proton --strip-components=1 \
    && rm proton.tar.gz

# Create gaming user with proper groups
RUN useradd -m -s /bin/bash -G sudo,audio,video gamer \
    && echo "gamer:gamer" | chpasswd \
    && mkdir -p /home/gamer/.config/sunshine \
    && chown -R gamer:gamer /home/gamer

# Copy configuration files
COPY sunshine.conf /home/gamer/.config/sunshine/sunshine.conf
COPY apps.json /home/gamer/.config/sunshine/apps.json
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Set permissions
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chown -R gamer:gamer /home/gamer/.config

# Expose Sunshine ports (TCP for HTTPS, UDP for streaming)
EXPOSE 47984/tcp 47989/udp 47990/tcp

# Environment variables for GPU access and display
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=all \
    DISPLAY=:0 \
    XDG_RUNTIME_DIR=/tmp/runtime-gamer \
    PULSE_RUNTIME_PATH=/tmp/runtime-gamer/pulse \
    STEAM_COMPAT_DATA_PATH=/home/gamer/.steam/steam/steamapps/compatdata

# Switch to gaming user
USER gamer
WORKDIR /home/gamer

# Create Steam directories
RUN mkdir -p .steam/steam/steamapps/compatdata \
    && mkdir -p .local/share/Steam/steamapps/common

# Health check: verify NVENC and Sunshine API
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ffmpeg -encoders 2>/dev/null | grep -q nvenc && \
        curl -f http://localhost:47990/api/config || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]