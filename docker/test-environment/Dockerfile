FROM ubuntu:22.04

# Prevent systemd from starting services during package installation
RUN echo '#!/bin/bash\nexit 0' > /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d

# Install systemd and other dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    systemd \
    systemd-sysv \
    sudo \
    python3 \
    python3-pip \
    openssh-server \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Remove policy file after installation
RUN rm -f /usr/sbin/policy-rc.d

# Setup SSH
RUN mkdir -p /var/run/sshd && \
    echo 'root:testpassword' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Create test user
RUN useradd -m -s /bin/bash testuser && \
    echo 'testuser:testpassword' | chpasswd && \
    usermod -aG sudo testuser

# Clean up systemd
RUN cd /lib/systemd/system/sysinit.target.wants/; \
    for i in *; do [ $i = systemd-tmpfiles-setup.service ] || rm -f $i; done && \
    rm -f /lib/systemd/system/multi-user.target.wants/* && \
    rm -f /etc/systemd/system/*.wants/* && \
    rm -f /lib/systemd/system/local-fs.target.wants/* && \
    rm -f /lib/systemd/system/sockets.target.wants/*udev* && \
    rm -f /lib/systemd/system/sockets.target.wants/*initctl* && \
    rm -f /lib/systemd/system/basic.target.wants/* && \
    rm -f /lib/systemd/system/anaconda.target.wants/*

# Enable systemd and SSH service
RUN systemctl set-default multi-user.target && \
    systemctl enable ssh && \
    systemctl mask systemd-networkd-wait-online.service

# Generate SSH host keys
RUN ssh-keygen -A

EXPOSE 22 80 443 3000 9090 3100

# Use exec form to ensure proper signal handling
CMD ["/sbin/init"]