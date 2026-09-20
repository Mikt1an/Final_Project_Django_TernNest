#!/bin/bash

sudo dnf update
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker


sudo usermod -aG docker ec2-user
#newgrp docker

#sudo mkdir -p /usr/local/lib/docker/cli-plugins
#sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" -o /usr/libexec/docker/cli-plugins/docker-compose
#sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose
# Download for x86_64 architecture
DOCKER_CLI_PLUGINS_DIR="/usr/local/lib/docker/cli-plugins"
sudo mkdir -p $DOCKER_CLI_PLUGINS_DIR
sudo curl -SL https://github.com/docker/buildx/releases/download/v0.25.0/buildx-v0.25.0.linux-amd64 -o $DOCKER_CLI_PLUGINS_DIR/docker-buildx
sudo chmod +x $DOCKER_CLI_PLUGINS_DIR/docker-buildx

#sudo dnf install -y docker-compose-plugin

sudo systemctl restart docker

dnf install -y git
cd /opt/
git clone https://github.com/AndreevVE/ich_django_final_project.git
cd ich_django_final_project
docker-compose up
