#!/bin/bash


yearmonth=`date +%Y%m`
tag="subset:$yearmonth"
podman build . -t $tag

podman save --format oci-archive $tag -o subset.tar

singularity build subset.sif oci-archive://subset.tar

export SINGULARITY_BINDPATH="/gpfs/csfs1/collections/rda/data:/gpfs/csfs1/collections/rda/data,/gpfs/csfs1/collections/rda/transfer:/gpfs/csfs1/collections/rda/transfer,/gpfs/csfs1/collections/rda/work:/gpfs/csfs1/collections/rda/work,/gpfs/u/home/rdadata/:/gpfs/u/home/rdadata/"
