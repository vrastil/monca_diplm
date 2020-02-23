#!/bin/bash
ROOT="./database"
BIND="-B ./data/:/var/lib/mongo -B ./logs/:/var/log/mongodb -B ./var_run_mongodb/:/var/run/mongodb"
IMG="/home/michal/GIT/web_spek_stovecka/private/database/mongodb-container.img"

cd $ROOT
singularity run ${BIND} ${IMG}

