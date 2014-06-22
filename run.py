#!/usr/bin/env python

# This script runs within a docker container on each host.  It's job is to 
# register and deregister containers on the host in etcd whenever they change.
# It should probably only register the service containers but I'll get it to 
# register everything to start with

#TODO:
#  Don't forget the etcd peers

"""
Keys should look like

/mayfly/backends/$SERVICE/$VERSION/$UUID/ip -> Host IP Address
/mayfly/backends/$SERVICE/$VERSION/$UUID/port/8080 -> Host port which maps to 8080 
/mayfly/backends/$SERVICE/$VERSION/$UUID/env -> Environment which this container supports
/mayfly/backends/$SERVICE/$VERSION/$UUID/healthcheck -> URL to hit to check service health (/ping/ping)
"""

from ClassyEtcd import *
import docker
import uuid, os

docker_client = docker.Client(base_url='unix://var/run/docker.sock')
host_ip = os.environ.get('HOST_IP', None) 
if not host_ip:
  raise ValueError('ENV variable HOST_IP missing')

root_node = getEtcdNode('')

for container in docker_client.containers():
  image_version = container['Image']
  image_name, version = image_version.split(':')
  service = image_name.split('/')[-1] # foo/bar:0.1 and bar:0.1 both -> bar
  u = uuid.uuid4().hex
  service_key = "/mayfly/backends/%s/%s/%s" % (service, version, u)
  ports = map(lambda p: (p['PrivatePort'], p['PublicPort']), filter(lambda p: 'PublicPort' in p, container['Ports']))
  root_node["%s/ip" % service_key] = host_ip
  for (priv, pub) in ports:
    root_node["%s/port/%s" % (service_key, priv)] = pub
  root_node["%s/env" % service_key] = 'default'
  root_node["%s/healthcheck" % service_key] = 'None'
