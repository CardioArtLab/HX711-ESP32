import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QDesktopWidget, 
    QMainWindow, QAction, QVBoxLayout, QLCDNumber, QDockWidget, QInputDialog, QFileDialog,
    QMessageBox)
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import serial
from serial.tools.list_ports import comports
from SerialThread import SerialThread

class Application(QMainWindow):

    def __init__(self):
        super().__init__()
        self.initUI()
        self.serial = None
        self.timer = QTimer(self)
        self.tData = []
        self.wData = []

    def initUI(self):
        
        toolbar = self.addToolBar('toolbar')
        action = QAction('Connect', self)
        action.setStatusTip('Connect COM port')
        action.triggered.connect(self.connectCOMDialog)
        toolbar.addAction(action)
        #exitAct.triggered.connect(self.close)
        #
        action = QAction('Disconnect', self)
        action.setStatusTip('Disconnect from serial COM port')
        action.triggered.connect(self.disconnect)
        toolbar.addAction(action)
        toolbar.addSeparator()

        action = QAction('Tare', self)
        action.setStatusTip('set OFFSET')
        action.triggered.connect(self.tare)
        toolbar.addAction(action)

        action =QAction('Calibrate', self)
        action.setStatusTip('Start calibrate weigh')
        action.triggered.connect(self.calibrate)
        toolbar.addAction(action)

        action = QAction('Set scale', self)
        action.setStatusTip('set prescale value to weigh')
        action.triggered.connect(self.setScaleDialog)
        toolbar.addAction(action)
        toolbar.addSeparator()

        action =QAction('Clear', self)
        action.setStatusTip('clear current data')
        action.triggered.connect(self.clearPlot)
        toolbar.addAction(action)

        self.plotWidget = pg.PlotWidget(self)
        self.plot = self.plotWidget.plot(pen=pg.mkPen('r', width=2))
        self.plotWidget.setLabel('bottom', 'Time', 'second')
        self.plotWidget.setLabel('left', 'Force', 'N')
        self.lcd = QLCDNumber(self)
        self.dock = QDockWidget("Weight", self)
        self.dock.setWidget(self.lcd)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.setCentralWidget(self.plotWidget)

        self.statusBar()

        self.resize(1000, 400)
        self.center()
        self.setWindowTitle('Weigh monitor')
        self.show()

    def center(self):
        
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def connectCOMDialog(self):
        ports = ','.join([x.device for x in comports()])
        port, ok = QInputDialog.getText(self, 'COM PORT', 'enter COM PORT: ' + ports )
        if ok:
            try:
                self.serial = serial.Serial(str(port), 9600, timeout=5)
                print(port)
                self.serialThread = SerialThread(self, self.serial)
                self.serialThread.data_received.connect(self.updateData)
                self.serialThread.start()
                self.setWindowTitle('Weigh monitor (' + port + ')')

                self.timer.timeout.connect(self.updatePlot)
                self.timer.start(300)
            except Exception as err:
                QMessageBox.warning(self, 'Error', str(err))

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serialThread.stopped()
            self.serial.close()
        self.setWindowTitle('Weigh monitor')

    def tare(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b'ATTARE\r\n')

    def calibrate(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b'ATCAL\r\n')

    def setScaleDialog(self):
        scale, ok = QInputDialog.getText(self, 'SET SCALE', 'enter scale (e.g. 10.013)')
        if ok:
            try:
                if self.serial and self.serial.is_open:
                    self.serial.write('ATSCALE={}\r\n'.format(float(scale)).encode('cp437'))                
            except Exception as err:
                QMessageBox.warning(self, 'Error', str(err))

    def saveDialog(self):
        filename = QFileDialog.getOpenFileName(self, 'Select save file', '', 'CSV file (*.csv);;All Files (*)')
        print(filename)
        
    def clearPlot(self):
        self.plot.clear()
        self.tData.clear()
        self.wData.clear()

    def updateData(self, time, value):
        self.lcd.display(str(value))
        self.tData.append(time)
        self.wData.append(value)

    def updatePlot(self):
        self.plot.setData(self.tData, self.wData)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    e = Application()
    sys.exit(app.exec_())
