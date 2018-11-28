from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal

class SerialThread(QThread):

    data_received = pyqtSignal(float, float)

    def __init__(self, parent=None, serial=None):
        QThread.__init__(self)
        self.parent = parent
        self.serial = serial

    def __del__(self):
        self.wait()

    def run(self):
        self.running = True
        while (self.running):
            try:
                line = self.serial.readline().strip().decode('cp437')
                tokens = line.split(' ')
                if len(tokens) >= 2:
                    time, value = tokens[0:2]
                    self.data_received.emit(float(time), float(value))
            except:
                pass

    def stopped(self):
        self.running = False