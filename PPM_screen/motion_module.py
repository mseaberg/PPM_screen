import numpy as np
import time
from pyqtgraph.Qt import QtCore
from ophyd import EpicsSignalRO as SignalRO
from ophyd import EpicsSignal as Signal
from pcdsdevices.signal import AvgSignal
from undpoint import UndPointDelta2D


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
        self.error_y = None
        self.new_error_y = None
        self.calib_y = None
        self.mirror_start = None
        self.undx_total = None
        self.undy_total = None

        if mirror_prefix == 'und':
            self.undulator = UndPointDelta2D(prefix="MFX:USER:MCC:UND",name='undulator')

        if 'L2' in self.imager_prefix:
            self.cam_name = self.imager_prefix + 'CAM:01:'
        elif 'IM' in self.imager_prefix:
            self.cam_name = self.imager_prefix + 'CAM:'
        else:
            self.cam_name = self.imager_prefix

        self.x_target = SignalRO(self.cam_name+'X_RTCL_CTR').get()
        self.y_target = SignalRO(self.cam_name+'Y_RTCL_CTR').get()
        x_centroid = SignalRO(self.cam_name+'X_BM_CTR')
        y_centroid = SignalRO(self.cam_name+'Y_BM_CTR')
        print(x_centroid.get())

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

        if self.running:

            # check centroid before moving anything
            cen_x, cen_y = self.get_centroid()
            print(cen_x - self.x_target)

            self.error = cen_x - self.x_target
            # move mirror slightly
            print('moving mirror')
            print(self.mirror.pitch.get())
            self.mirror_start = self.mirror.pitch.get()
            self.mirror.pitch.mvr(1, wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target
            self.calib = (self.new_error - self.error) / 1
            print('calibration: {} um/urad'.format(self.calib))
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
        else:
            self.sig_finished.emit()

    def _update(self):
        if self.running:

            if np.isnan(self.new_error):
                print('Beam down? Canceling...')
                self.mirror.pitch.mv(self.mirror_start, wait=True)
                self.sig_finished.emit()
                return
            try:
                adj = -self.new_error / self.calib * 0.9
            except ZeroDivisionError:
                print('problem with calibration')
                self.mirror.pitch.mv(self.mirror_start, wait=True)
                self.sig_finished.emit()
                return

            print(adj)
            if np.abs(adj)>2:
                adj = np.sign(adj)*2
            self.mirror.pitch.mvr(adj, wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target
            print(self.new_error)
            if np.abs(self.new_error)>20:
                QtCore.QTimer.singleShot(200, self._update)
            else:
                print('alignment completed')

                self.sig_finished.emit()
        else:
            print('Alignment canceled, moving back to start')
            self.mirror.pitch.mv(self.mirror_start, wait=True)
            self.sig_finished.emit()

    def _und_run(self):
        # need to get some updates from the RunProcessing object to see where we are currently. We also need to

        # need a while loop here to collect some data

        if self.running:

            # check centroid before moving anything
            cen_x, cen_y = self.get_centroid()
            print(cen_x - self.x_target)

            self.error = cen_x - self.x_target
            self.error_y = cen_y - self.y_target
            # move undulator slightly
            self.undulator.move(position=(20,20),wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target
            self.new_error_y = cen_y - self.y_target
            self.calib = (self.new_error - self.error) / 20
            self.calib_y = (self.new_error_y - self.error_y) / 20
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
        else:
            self.sig_finished.emit()

    def _und_update(self):
        if self.running:
            if np.isnan(self.new_error):
                print('Beam down? Canceling...')
                self.sig_finished.emit()
                return
            try:
                adj = -self.new_error / self.calib * 0.9
                adj_y = -self.new_error_y / self.calib_y * 0.9
            except ZeroDivisionError:
                print('problem with calibration')
                self.sig_finished.emit()
                return


            print(adj)
            if np.abs(adj)>50:
                adj = np.sign(adj)*50
            if np.abs(adj_y)>50:
                adj_y = np.sign(adj_y)*50
            self.undulator.move((adj,adj_y), wait=True)
            cen_x, cen_y = self.get_centroid()
            self.new_error = cen_x - self.x_target
            self.new_error_y = cen_y - self.y_target
            print(self.new_error_y)
            if np.abs(self.new_error)>20 or np.abs(self.new_error_y)>20:
                QtCore.QTimer.singleShot(200, self._und_update)
            else:
                print('alignment completed')

                self.sig_finished.emit()
        else:
            self.sig_finished.emit()

    def cancel(self):
        self.running = False


class Motor():
    def __init__(self, pv_name):
        self.setpoint = Signal(pv_name)
        self.rbv = SignalRO(pv_name+'.RBV')
        self.moving = SignalRO(pv_name + '.MOVN')

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
        return self.rbv.get()

    def set(self, target):
        self.setpoint.set(target)

class Attenuate(QtCore.QObject):
    sig_finished = QtCore.pyqtSignal()

    def __init__(self):
        super(Attenuate, self).__init__()
        self.calculate = Signal('AT2L0:CALC:SYS:Run')
        self.apply = Signal('AT2L0:CALC:SYS:ApplyConfiguration')
        self.status = None

    def run(self):
        # run calculation
        self.status = self.calculate.set(1)
        #while not self.status.done:
        #    time.sleep(0.1)
        #print('finished calculating')
        self.status.wait()

        # apply configuration
        self.status = self.apply.set(1)
        self.status.wait()

        self.sig_finished.emit()


class Mirror():

    def __init__(self, mirror_base, name=None):
        # initialize attributes
        self.name = name
        self.mirror_base = mirror_base
        self.motor_base = self.mirror_base + ':MMS'
        # initialize epics signals
        self.pitch = Motor(self.motor_base+':PITCH')
