import numpy as np
import time
from pyqtgraph.Qt import QtCore
from ophyd import EpicsSignalRO as SignalRO
from ophyd import EpicsSignal as Signal
from pcdsdevices.signal import AvgSignal
from undpoint import UndPointDelta2D
import os


class Alignment(QtCore.QObject):

    sig_finished = QtCore.pyqtSignal()

    def __init__(self, curr_imager_dict):
        super(Alignment, self).__init__()

        self.imager_prefix = curr_imager_dict['prefix']
        mirror_prefix = curr_imager_dict['mirror']
        self.mirror = Mirror(mirror_prefix)
        self.undulator = None
        self.calib = None
        self.error = None
        self.new_error = None

        if mirror_prefix == 'und':
            self.undulator = UndPointDelta2D(prefix="MFX:USER:MCC:UND",name='undulator')

        if 'L2' in self.imager_prefix:
            self.cam_name = self.imager_prefix + 'CAM:01:'
        elif 'IM' in self.imager_prefix:
            self.cam_name = self.imager_prefix + 'CAM:'
        else:
            self.cam_name = self.imager_prefix

        self.x_target = SignalRO(self.cam_name+'X_RTCL_CTR', auto_monitor=True)
        self.y_target = SignalRO(self.cam_name+'Y_RTCL_CTR', auto_monitor=True)
        x_centroid = SignalRO(self.imager_prefix+'X_BM_CTR')
        y_centroid = SignalRO(self.imager_prefix+'Y_BM_CTR')


        self.avg_x_centroid = AvgSignal(x_centroid, 10, 2, name='avg_x_centroid')
        self.avg_y_centroid = AvgSignal(y_centroid, 10, 2, name='avg_y_centroid')

    def get_centroid(self):
        status_x = self.avg_x_centroid.trigger()
        status_y = self.avg_y_centroid.trigger()
        all_status = [status_x, status_y]

        done_reading = False

        while not done_reading:
            time.sleep(0.1)
            done_reading = all([status.done for status in all_status])
        out_x = self.avg_x_centroid.get()
        out_y = self.avg_y_centroid.get()
        # make sure we get a good reading before continuing
        # if np.isnan(out):
        #     print('need to get a better signal')
        #     self.get_centroid()
        return out_x, out_y

    def run(self):

        self.running = True
        if self.undulator is not None:
            self._und_run()
        else:
            self._run()

    def _run(self):
        # need to get some updates from the RunProcessing object to see where we are currently. We also need to

        # need a while loop here to collect some data

        if self.running:

            # check centroid before moving anything
            cen_x, cen_y = self.get_centroid()
            print(cen_x - self.x_target.value)

            self.error = cen_x - self.x_target.value
            # move mirror slightly
            print('moving mirror')
            print(self.mirror.pitch.get())
            #self.mirror.pitch.mvr(0.2, wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target.value
            self.calib = (self.new_error - self.error) / 0.2
            self._update()
            # print(self.new_error)
            # #while np.abs(new_error) > 50:
            # condition = True
            # while condition:
            #     adj = -new_error / self.calib
            #     print(adj)
            #     #self.mirror.pitch.mvr(adj, wait=True)
            #     cen_x, cen_y = self.get_centroid()
            #     new_error = cen_x - self.x_target.value
            #     print(new_error)
            #     time.sleep(.1)
            #     condition = False
            # print('alignment completed')
            #
            # self.sig_finished.emit()

    def _update(self):
        if self.running:

            adj = -self.new_error / self.calib
            print(adj)
            # self.mirror.pitch.mvr(adj, wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target.value
            print(self.new_error)
            if self.new_error>20:
                QtCore.QTimer.singleShot(200, self._update)
            else:
                print('alignment completed')

                self.sig_finished.emit()

    def _und_run(self):
        # need to get some updates from the RunProcessing object to see where we are currently. We also need to

        # need a while loop here to collect some data

        if self.running:

            # check centroid before moving anything
            cen_x, cen_y = self.get_centroid()
            print(cen_x - self.x_target.value)

            self.error = cen_x - self.x_target.value
            # move undulator slightly
            #self.undulator.move(position=20, wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target.value
            calib = (self.new_error - self.error) / 0.2
            print(self.new_error)
            self._und_update()
            # #while np.abs(new_error) > 50:
            # condition = True
            # while condition:
            #     adj = -new_error / calib
            #     print(adj)
            #     #self.undulator.move(position=adj, wait=True)
            #     cen_x, cen_y = self.get_centroid()
            #     new_error = cen_x - self.x_target.value
            #     print(new_error)
            #     time.sleep(.1)
            #     condition = False
            # print('alignment completed')
            #
            # self.sig_finished.emit()

    def _und_update(self):
        if self.running:

            adj = -self.new_error / self.calib
            print(adj)
            # self.undulator.move(adj, wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target.value
            print(self.new_error)
            if self.new_error>20:
                QtCore.QTimer.singleShot(200, self._und_update)
            else:
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
