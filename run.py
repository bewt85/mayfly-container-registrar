#!/usr/bin/env python

# This script runs within a docker container on each host.  It's job is to 
# register and deregister containers on the host in etcd whenever they change.
# It should probably only register the service containers but I'll get it to 
# register everything to start with

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

class Backend(object):
  def __init__(self, service, version, uuid, host_ip, ports, env='default', healthcheck='None'):
    self.service = service
    self.version = version
    self.uuid = uuid
    self.host_ip = host_ip
    self.ports = ports
    self.env = env
    self.healthcheck = healthcheck
  def addToEtcd(self):
    root_node = getEtcdNode('')
    service_key = "/mayfly/backends/%s/%s/%s" % (self.service, self.version, sel.uuid)
    root_node["%s/ip" % service_key] = self.host_ip
    for (priv, pub) in self.ports:
      root_node["%s/port/%s" % (service_key, priv)] = pub
    root_node["%s/env" % service_key] = self.env
    root_node["%s/healthcheck" % service_key] = self.healthcheck
  def removeFromEtcd(self):
    print "WARNING: not implemented, cannot remove %s" % self
  def __eq__(self, other):
    return hash(self) == hash(other)
  def __repr__(self):
    return str(self.__dict__)
  def __hash__(self):
    withoutUuid = dict((key, value) for key, value in self.__dict__.items() if key != 'uuid')
    withSortedPorts = withoutUuid.update({'ports': sorted(self.ports)})
    return hash(withSortedPorts)

class BackendFactory(object):
  def fromEtcd(self):
    backend_nodes = getEtcdNode('/mayfly/backends/')
    for service_nodes in backend_nodes.ls():
      service = service_nodes.short_key
      for version_nodes in service_nodes.ls():
        version = version_nodes.short_key
        for uuid_node in version_nodes.ls():
          u = uuid_node.short_key
          env = uuid_node['env'].value if uuid_node.get('env') else None
          host_ip = uuid_node['ip'].value
          healthcheck = uuid_node['healthcheck'].value if uuid_node.get('healthcheck') else None
          ports = map(lambda n: (n.short_key, n.value), uuid_node['port'].ls())
          yield Backend(service, version, u, host_ip, ports, env, healthcheck)
  def fromDocker(self):
    for container in docker_client.containers():
      image_version = container['Image']
      image_name, version = image_version.split(':')
      service = image_name.split('/')[-1] # foo/bar:0.1 and bar:0.1 both -> bar
      u = uuid.uuid4().hex
      ports = map(lambda p: (p['PrivatePort'], p['PublicPort']), filter(lambda p: 'PublicPort' in p, container['Ports']))
      yield Backend(service, version, u, host_ip, ports)

factory = BackendFactory()

latest_containers = list(factory.fromDocker())
existing_containers = list(factory.fromEtcd())

duplicate_existing_containers = []
unique_existing_containers = []

for container in existing_containers:
  if container in unique_existing_containers:
    duplicate_existing_containers.append(container)
  else:
    unique_existing_containers.append(container)

new_containers = filter(lambda l: l not in existing_containers, latest_containers)
unchanged_containers = filter(lambda l: l in existing_containers, latest_containers)
old_containers = filter(lambda e: e not in latest_containers, existing_containers)

for container in new_containers:
  container.addToEtcd()
for container in old_containers:
  container.removeFromEtcd()
for container in duplicate_existing_containers:
  container.removeFromEtcd()

