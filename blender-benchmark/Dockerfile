FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

# Install Blender dependencies, tools and python (system)
RUN apt-get update && apt-get install -y \
    xz-utils \
    libglu1-mesa \
    libgl1 \
    libgl1-mesa-glx \
    libegl1 \
    libxrender1 \
    libxi6 \
    libxkbcommon0 \
    libsm6 \
    wget \
    tar \
    tree \
    nano \
    curl \
    net-tools \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Optional: Install VS Code Server
RUN curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' -o vscode_cli.tar.gz && \
    tar -xf vscode_cli.tar.gz && \
    mv code /usr/local/bin/code && \
    rm vscode_cli.tar.gz

# To connect using VS Code:
# Log in the instance using the terminal, and then run the following commands:
# code tunnel user login --provider github
# nohup code tunnel --accept-server-license-terms --name 001 &> output.log &

# Download Blender 4.5 precompiled binary
RUN wget https://download.blender.org/release/Blender4.5/blender-4.5.0-linux-x64.tar.xz \
    && tar -xf blender-4.5.0-linux-x64.tar.xz -C /opt/ \
    && rm blender-4.5.0-linux-x64.tar.xz
   
# Add Blender to PATH
ENV PATH="$PATH:/opt/blender-4.5.0-linux-x64"

WORKDIR /app

# Downlowd and run Blender Benchmark Launcher - Linux CLI on the WSL
# https://opendata.blender.org/
# Then copy the downloaded scenes (monster, junkshop, classroom) from the host to the container image
# ~/.cache/blender-benchmark-launcher -> the current folder ->  /root/.cache/blender-benchmark-launcher
COPY blender-benchmark-launcher /root/.cache/blender-benchmark-launcher
RUN chmod -R 777 /root/.cache/blender-benchmark-launcher

# Copy the downloaded Blender Benchmark Launcher - Linux CLI to the container image
COPY benchmark-launcher-cli /app/
RUN chmod +x /app/benchmark-launcher-cli

# Upgrade pip 
RUN pip install --upgrade pip
RUN pip install python-dotenv speedtest-cli pythonping requests
RUN pip install jupyterlab ipywidgets tzdata

COPY helper.py init_check.py benchmark.py start.sh Dockerfile /app/
RUN chmod +x /app/start.sh

# Set environment variables for CUDA
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics

# Default command: test 
# CMD ["./start.sh"]

# Default command: benchmark 
CMD ["python3", "benchmark.py"]