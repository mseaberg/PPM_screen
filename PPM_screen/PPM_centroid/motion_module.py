import numpy as np
import time
from pyqtgraph.Qt import QtCore
from ophyd import EpicsSignalRO as SignalRO
from ophyd import EpicsSignal as Signal
from pcdsdevices.signal import AvgSignal
import os


class Alignment(QtCore.QObject):

    sig_finished = QtCore.pyqtSignal()

    def __init__(self, curr_imager_dict):
        super(Alignment, self).__init__()

        self.imager_prefix = curr_imager_dict['prefix']
        mirror_prefix = curr_imager_dict['mirror']
        self.mirror = Mirror(mirror_prefix)

        if 'L2' in self.imager_prefix:
            self.cam_name = self.imager_prefix + 'CAM:01:'
        elif 'IM' in self.imager_prefix:
            self.cam_name = self.imager_prefix + 'CAM:'
        else:
            self.cam_name = self.imager_prefix

        self.target = SignalRO(self.cam_name+'X_RTCL_CTR', auto_monitor=True)
        centroid = SignalRO(self.imager_prefix+'X_BM_CTR')

        self.avg_centroid = AvgSignal(centroid, 10, 2, name='avg_centroid')

    def get_centroid(self):
        status = self.avg_centroid.trigger()
        while not status.done:
            time.sleep(0.1)
        out = self.avg_centroid.get()
        # make sure we get a good reading before continuing
        if np.isnan(out):
            print('need to get a better signal')
            self.get_centroid()
        return out

    def run(self):

        self.running = True
        self._update()

    def _update(self):
        # need to get some updates from the RunProcessing object to see where we are currently. We also need to

        # need a while loop here to collect some data

        if self.running:

            # check centroid before moving anything
            cen = self.get_centroid()
            print(cen - self.target.value)

            error = cen - self.target.value
            # move mirror slightly
            print('moving mirror')
            print(self.mirror.pitch.get())
            #self.mirror.pitch.mvr(0.2, wait=True)
            cen = self.get_centroid()
            new_error = cen - self.target.value
            calib = (new_error - error) / 0.2
            print(new_error)
            #while np.abs(new_error) > 50:
            condition = True
            while condition:
                adj = -new_error / calib
                print(adj)
                #self.mirror.pitch.mvr(adj, wait=True)
                new_error = self.get_centroid() - self.target.value
                print(new_error)
                time.sleep(.1)
                condition = False
            print('alignment completed')

            self.sig_finished.emit()

    def cancel(self):
        self.running = False


class Motor():
    def __init__(self, pv_name):
        self.setpoint = Signal(pv_name)
        self.rbv = SignalRO(pv_name+'.RBV', auto_monitor=True)
        self.moving = SignalRO(pv_name + '.MOVN', auto_monitor=True)

    def mv(self, target, wait=True):
        self.set(target)
        if wait:
            # while np.abs(self.get() - target) > tol:
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
