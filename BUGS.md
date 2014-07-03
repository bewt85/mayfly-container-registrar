# Bugs

- It cannot start registering containers if '/mayfly/backends' does not exist
- If there are problems parsing etcd, the container registrar falls over
- The container registrar cannot cope with some sorts of containers (e.g. those not from a tagged image)
- It's not actually pulling out anything to do with environments
