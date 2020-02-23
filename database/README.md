### enable auth

note: it's briliant idea to do not use password `admin123` like in the example below.

```
use admin
db.dropUser('admin')
db.createUser({user:'admin',pwd:'admin123',roles:[{role:"userAdminAnyDatabase",db:"admin"},"readWriteAnyDatabase"],passwordDigestor:"server"})
```

### build container

```
sudo singularity build mongodb-container.img ./mongodb-container.def
```

### start shell inside container

```
singularity shell -B ./data/:/var/lib/mongo -B ./logs/:/var/log/mongodb -B ./var_run_mongodb/:/var/run/mongodb ./mongodb-container.img
```

### run container with db

```
singularity run -B ./data/:/var/lib/mongo -B ./logs/:/var/log/mongodb -B ./var_run_mongodb/:/var/run/mongodb ./mongodb-container.img
```

### start db in singularity shell


#### without auth:

```
mongod --config /etc/mongod.conf
```

#### with auth set up:
```
mongod --config /etc/mongod.conf --auth
```
# monca_diplm
