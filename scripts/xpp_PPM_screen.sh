#!/bin/env bash
#source /cds/home/s/seaberg/setup_python.sh
#source /reg/g/pcds/pyps/apps/hutch-python/xcs/xcsenv
#source /reg/g/pcds/pyps/apps/hutch-python/tmo/tmoenv
#source /reg/g/pcds/pyps/apps/hutch-python/xpp/xppenv

#source /cds/home/s/seaberg/beamlineconda.sh
source /reg/g/pcds/pyps/apps/hutch-python/xpp/xppenv
export PYTHONPATH=$PYTHONPATH:/cds/home/s/seaberg/Python/PPM_screen
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_NUM_THREADS=1

#cd /cds/home/s/seaberg/TMO_IP2/Commissioning_Tools/PPM_centroid
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

HERE=`dirname $(readlink -f $0)`

if [ $# -eq 1 ]; then
    IMAGER=$1
else
    IMAGER="IM3L0"
fi

python $HERE/../PPM_screen/run_interface.py -c $IMAGER &
