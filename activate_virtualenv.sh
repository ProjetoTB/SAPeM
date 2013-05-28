#!/usr/bin/env bash

source /usr/local/projetotb-py27/bin/activate
mkdir -p $2
chmod 777 $2
python $1 $2 $3
deactivate
