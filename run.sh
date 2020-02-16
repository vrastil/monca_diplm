#!/bin/bash

singularity run -B ./data/:/var/lib/mongo -B ./logs/:/var/log/mongodb -B ./var_run_mongodb/:/var/run/mongodb ~/GIT/web_spek_stovecka/private/database/mongodb-container.img
# singularity exec -B ./data/:/var/lib/mongo -B ./logs/:/var/log/mongodb -B ./var_run_mongodb/:/var/run/mongodb ~/GIT/web_spek_stovecka/private/database/mongodb-container.img mongod --config /etc/mongod.conf 
