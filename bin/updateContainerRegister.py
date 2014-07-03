#!/usr/bin/env python

# This script runs within a docker container on each host.  It's job is to 
# register and deregister containers on the host in etcd whenever they change.
# It should probably only register the service containers but I'll get it to 
# register everything to start with

from Backend import BackendFactory

factory = BackendFactory()

latest_containers = list(factory.fromDocker())
existing_containers = list(factory.fromEtcd())

new_containers = filter(lambda l: l not in existing_containers, latest_containers)
old_containers = filter(lambda e: e not in latest_containers, existing_containers)

for container in new_containers:
  container.addToEtcd()
for container in old_containers:
  container.removeFromEtcd()

