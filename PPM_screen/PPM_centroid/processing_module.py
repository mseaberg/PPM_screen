from epics import PV, caget
import numpy as np
import time
from pyqtgraph.Qt import QtCore
from PPM_screen.PPM_centroid import optics
import pandas as pd
from ophyd import EpicsSignalRO as SignalRO


class RunProcessing(QtCore.QObject):
    sig = QtCore.pyqtSignal()
    sig_initialized = QtCore.pyqtSignal()
    sig_finished = QtCore.pyqtSignal()

    def __init__(self, imager_prefix, data_handler, averageWidget, threshold=0.1, thread=None, hutch=None, crossWidget=None):
        super(RunProcessing, self).__init__()
        #QtCore.QThread.__init__(self)

        self.thread = thread
        self.hutch = hutch

        if crossWidget is not None:
            try:
                x1 = float(crossWidget.red_x.text())
                y1 = float(crossWidget.red_y.text())
                x2 = float(crossWidget.blue_x.text())
                y2 = float(crossWidget.blue_y.text())
                roi = [x1,y1,x2,y2]
            except:
                roi = None

        else:
            roi = None

        self.hutch_path = '/cds/home/opr/{}opr'.format(self.hutch.lower())
        if 'L2' in imager_prefix:
            self.hutch_path = '/sdf/home/x/xppopr'

        # set threshold attribute (defaults to 0.1)
        self.threshold = threshold

        # PPM object for image acquisition and processing
        self.PPM_object = optics.PPM_Device(imager_prefix, average=averageWidget, threshold=self.threshold, roi=roi)

        # frame rate initialization
        self.fps = 0.
        self.lastupdate = time.time()

        # initialize data handler
        self.data_handler = data_handler

        self.timer = None

        #### Start  #####################
        # self._update()

    def run(self):
       
        # check if data handler is initialized
        if self.data_handler.initialized:
            # just update PPM object
            self.data_handler.update_imager(self.PPM_object)
        else:
            self.data_handler.initialize(self.PPM_object)

        self.running = True
        self.sig_initialized.emit()

        self.timer = QtCore.QTimer()
        if self.hutch=='lfe':
            self.timer.setInterval(2000)
        else:
            self.timer.setInterval(500)
        self.timer.timeout.connect(self._update)

        #self._update()
        self.timer.start()

    def save_data(self, filename):
        self.data_handler.save_data(filename)

    def reset_plots(self):
        self.data_handler.reset_data()

    def set_orientation(self, orientation):
        self.PPM_object.set_orientation(orientation)

    def get_FOV(self):
        width = self.PPM_object.FOV
        height = np.copy(width)
        return width, height

    def _update(self):

        if self.running:

            # get latest image
            self.PPM_object.get_image(angle=angle)

            # send data
            self.sig.emit()

            # keep running unless the stop button is pressed
            if self.running:
                #QtCore.QTimer.singleShot(500, self._update)
                pass
            else:
                self.PPM_object.reset_camera()
                self.sig_finished.emit()
                self.timer.stop()
        else:
            self.sig_finished.emit()
            self.timer.stop()

    def stop(self):
        self.running = False
        self.PPM_object.stop()
