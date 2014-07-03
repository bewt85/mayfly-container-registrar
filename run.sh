#!/bin/bash

set -e

if [[ $EUID -ne 0 ]]; then
  echo "Must be run as root" 
  exit 1
fi

if [[ -z $DOCKER_ACCOUNT_NAME ]]; then
  DOCKER_ACCOUNT_NAME="bewt85"
fi

HOST_IP=`ifconfig eth0 | awk '/inet addr/ {print $2}' | cut -d: -f2`
docker run -d -t -e HOST_IP=$HOST_IP -e ETCD_PEERS=${HOST_IP}:9000 -v /var/run/docker.sock:/var/run/docker.sock ${DOCKER_ACCOUNT_NAME}/container_registrar
