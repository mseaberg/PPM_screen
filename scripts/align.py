import numpy as np
import time
from ophyd import EpicsSignalRO as SignalRO
from ophyd import EpicsSignal as Signal
import os
from pcdsdevices.signal import AvgSignal


class Motor():
    def __init__(self, pv_name):
        self.setpoint = Signal(pv_name)
        self.rbv = SignalRO(pv_name+'.RBV',auto_monitor=True)
        self.moving = SignalRO(pv_name+'.MOVN',auto_monitor=True)

    def mv(self, target, wait=True):
        self.set(target)
        if wait:
            #while np.abs(self.get() - target) > tol:
            #    time.sleep(0.2)
            moving_status = True
            while moving_status:
                moving_status = self.moving.get()
                time.sleep(0.1)
        print('move completed')

    def mvr(self, adjustment, wait=True):
        target = self.get() + adjustment
        self.mv(target, wait=wait)

    def get(self):
        return self.rbv.value

    def set(self, target):
        self.setpoint.set(target)



class Mirror():

    def __init__(self, mirror_base, name=None):
        # initialize attributes
        self.name = name
        self.mirror_base = mirror_base
        self.motor_base = self.mirror_base + ':MMS'
        # initialize epics signals
        self.pitch = Motor(self.motor_base+':PITCH')


target = SignalRO('XRT:DG3:GIGE:01:X_RTCL_CTR',auto_monitor=True)
centroid = SignalRO('XRT:DG3:GIGE:01:X_BM_CTR')
avg_centroid = AvgSignal(centroid,10,2,name='avg_centroid')

def get_centroid():
    status = avg_centroid.trigger()
    while not status.done:
        time.sleep(0.1)
    out = avg_centroid.get()
    # make sure we get a good reading before continuing
    if np.isnan(out):
        print('need to get a better signal')
        get_centroid()
    return out

mirror = Mirror('MR2L0:HOMS')

# check centroid before moving anything
cen = get_centroid()
print(cen-target.value)

error = cen - target.value
# move mirror slightly
print('moving mirror')
mirror.pitch.mvr(0.2,wait=True)
cen = get_centroid()
new_error = cen - target.value
calib = (new_error - error)/0.2
print(new_error)
while np.abs(new_error) > 50:
    adj = -new_error/calib
    print(adj)
    mirror.pitch.mvr(adj,wait=True)
    new_error = get_centroid() - target.value
    print(new_error)
    time.sleep(.1)
print('alignment completed')
