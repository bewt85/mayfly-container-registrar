mayfly-container-registrar
==========================

This is part of [mayfly](https://github.com/bewt85/mayfly) which demonstrates the 
concept of testing groups of versions of services in short lived virtual environments.

This is a docker container which runs a script to publishes the details of new containers to etcd. 
These changes are picked up by [haproxy_updater](https://github.com/bewt85/mayfly-haproxy-updater) 
which in turn updates [haproxy](https://github.com/bewt85/docker-haproxy).

Personally I think it would be better to rip out this container and etcd and replace both with 
[consul](https://github.com/hashicorp/consul) and some proper health checks.

You can build your own versions of the ontainers by setting the following environment variable 
to your docker index username (if you don't it uses mine) and running this bash script:

```
export DOCKER_ACCOUNT_NAME=<your_name>
sudo -E ./build.sh
```
