#!/usr/bin/env python

# This script runs within a docker container on each host.  It's job is to 
# register and deregister containers on the host in etcd whenever they change.
# It should probably only register the service containers but I'll get it to 
# register everything to start with

"""
Keys should look like

/mayfly/backends/$SERVICE/$VERSION/$MD5/ip -> Host IP Address
/mayfly/backends/$SERVICE/$VERSION/$MD5/port/8080 -> Host port which maps to 8080 
/mayfly/backends/$SERVICE/$VERSION/$MD5/env -> Environment which this container supports
/mayfly/backends/$SERVICE/$VERSION/$MD5/healthcheck -> URL to hit to check service health (/ping/ping)
"""

from ClassyEtcd import *
import docker
import os, hashlib

docker_client = docker.Client(base_url='unix://var/run/docker.sock')

host_ip = os.environ.get('HOST_IP', None) 
if not host_ip:
  raise ValueError('ENV variable HOST_IP missing')

class Backend(object):
  def __init__(self, service, version, host_ip, ports, env='default', healthcheck='None', md5=None):
    self.service = service
    self.version = version
    self.host_ip = host_ip
    self.ports = ports
    self.env = env
    self.healthcheck = healthcheck
    self.original_md5 = md5 
  def addToEtcd(self):
    root_node = getEtcdNode('')
    self.original_md5 = None
    service_key = "/mayfly/backends/%s/%s/%s" % (self.service, self.version, self.md5())
    root_node["%s/ip" % service_key] = self.host_ip
    for (priv, pub) in self.ports:
      root_node["%s/port/%s" % (service_key, priv)] = pub
    root_node["%s/env" % service_key] = self.env
    root_node["%s/healthcheck" % service_key] = self.healthcheck
  def removeFromEtcd(self):
    service_key = "/mayfly/backends/%s/%s/%s" % (self.service, self.version, self.md5())
    backend_node = getEtcdNode(service_key)
    backend_node.rm()
  def __eq__(self, other):
    return self.md5() == other.md5() 
  def __repr__(self):
    return str(self.__dict__)
  def md5(self):
    if self.original_md5:
      return self.original_md5
    else:
      m = hashlib.md5()
      m.update(str(self.service))
      m.update(str(self.version))
      m.update(str(self.host_ip))
      m.update(str(sorted(self.ports)))
      m.update(str(self.env))
      m.update(str(self.healthcheck))
      return m.hexdigest() 

class BackendFactory(object):
  def fromEtcd(self):
    backend_nodes = getEtcdNode('/mayfly/backends/')
    for service_nodes in backend_nodes.ls():
      service = service_nodes.short_key
      for version_nodes in service_nodes.ls():
        version = version_nodes.short_key
        for md5_node in version_nodes.ls():
          md5 = md5_node.short_key
          env = md5_node['env'].value if md5_node.get('env') else None
          host_ip = md5_node['ip'].value
          healthcheck = md5_node['healthcheck'].value if md5_node.get('healthcheck') else None
          ports = map(lambda n: (n.short_key, n.value), md5_node['port'].ls())
          yield Backend(service, version, host_ip, ports, env, healthcheck, md5=md5)
  def fromDocker(self):
    for container in docker_client.containers():
      image_version = container['Image']
      image_name, version = image_version.split(':')
      service = image_name.split('/')[-1] # foo/bar:0.1 and bar:0.1 both -> bar
      ports = map(lambda p: (p['PrivatePort'], p['PublicPort']), filter(lambda p: 'PublicPort' in p, container['Ports']))
      yield Backend(service, version, host_ip, ports)

factory = BackendFactory()

latest_containers = list(factory.fromDocker())
existing_containers = list(factory.fromEtcd())

new_containers = filter(lambda l: l not in existing_containers, latest_containers)
unchanged_containers = filter(lambda l: l in existing_containers, latest_containers)
old_containers = filter(lambda e: e not in latest_containers, existing_containers)

print "New Containers"
for container in new_containers:
  print container.md5(), container
  container.addToEtcd()
print
print
print "Old Containers"
for container in old_containers:
  print container.md5(), container
  container.removeFromEtcd()
print
print
print "Unchanged Containers"
for container in unchanged_containers:
  print container.md5(), container

