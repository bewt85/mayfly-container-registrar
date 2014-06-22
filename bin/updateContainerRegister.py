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
  def __init__(self, service, version, host_ip, ports, cid, env=u'default', healthcheck=u'None'):
    self.service = service
    self.version = version
    self.host_ip = host_ip
    self.ports = ports
    self.cid = cid
    self.env = env
    self.healthcheck = healthcheck
  def addToEtcd(self):
    root_node = getEtcdNode('')
    self.original_md5 = None
    service_key = "/mayfly/backends/%s/%s/%s" % (self.service, self.version, self.cid)
    root_node["%s/ip" % service_key] = self.host_ip
    for (priv, pub) in self.ports:
      root_node["%s/port/%s" % (service_key, priv)] = pub
    root_node["%s/env" % service_key] = self.env
    root_node["%s/healthcheck" % service_key] = self.healthcheck
  def removeFromEtcd(self):
    service_key = "/mayfly/backends/%s/%s/%s" % (self.service, self.version, self.cid)
    backend_node = getEtcdNode(service_key)
    backend_node.rm()
  def __eq__(self, other):
    return self.md5() == other.md5() 
  def __repr__(self):
    return str(self.__dict__)
  def md5(self):
    m = hashlib.md5()
    m.update(self.service)
    m.update(self.version)
    m.update(self.host_ip)
    m.update(unicode(sorted(self.ports)))
    m.update(self.cid)
    m.update(self.env)
    m.update(self.healthcheck)
    return m.hexdigest() 

class BackendFactory(object):
  def fromEtcd(self):
    backend_nodes = getEtcdNode('/mayfly/backends/')
    for service_nodes in backend_nodes.ls():
      service = service_nodes.short_key
      for version_nodes in service_nodes.ls():
        version = version_nodes.short_key
        for cid_node in version_nodes.ls():
          cid = cid_node.short_key
          env = cid_node['env'].value if cid_node.get('env') else None
          host_ip = cid_node['ip'].value
          healthcheck = cid_node['healthcheck'].value if cid_node.get('healthcheck') else None
          ports = map(lambda n: (n.short_key, n.value), cid_node['port'].ls() if cid_node.get('port') else [])
          yield Backend(service, version, host_ip, ports, cid, env, healthcheck)
  def fromDocker(self):
    for container in docker_client.containers():
      image_version = container['Image']
      image_name, version = image_version.split(':')
      service = image_name.split('/')[-1] # foo/bar:0.1 and bar:0.1 both -> bar
      ports = map(lambda p: (unicode(p['PrivatePort']), unicode(p['PublicPort'])), filter(lambda p: 'PublicPort' in p, container['Ports']))
      cid = container['Id']
      yield Backend(service, version, host_ip, ports, cid)

factory = BackendFactory()

latest_containers = list(factory.fromDocker())
existing_containers = list(factory.fromEtcd())

new_containers = filter(lambda l: l not in existing_containers, latest_containers)
old_containers = filter(lambda e: e not in latest_containers, existing_containers)

for container in new_containers:
  container.addToEtcd()
for container in old_containers:
  container.removeFromEtcd()
