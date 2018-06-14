from __future__ import division
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
from numpy import arange, sin, cos, pi
import pyqtgraph as pg
import sys
import scipy.fftpack as spfft
import scipy.signal as scisig
import serial

def filter(data):
	bp = spfft.fft(data)
	for i in range(len(bp)):
		if i >= 10:
			bp[i] = 0
	return spfft.ifft(bp)

class serial_data(object):

	def __init__(self, port, brate, timeout):
		self.ser = serial.Serial()
		self.ser.port = port
		self.ser.baudrate = brate
		self.ser.timeout = timeout
		print("Reading from port " + "\"" + str(self.ser.name) + "\"")

	def open(self):
		self.ser.open()
		print("Opening Port " + self.ser.port)

	def readLine(self):
		return self.ser.readline()

	def exit(self):
		self.ser.close()
		print("Closing Port " + self.ser.port)


class Window(QtGui.QMainWindow):

	def __init__(self):
		self.serData = serial_data('/dev/ttyACM0', 57600, 5)
		self.started = 0
		self.freq = 1
		self.N = 1000
		self.winSize = 1
		self.Fs = 250
		self.T = 1 / self.Fs 
		self.time = 0.0
		self.x = np.arange(0, 3, self.T)
		self.t = np.zeros(len(self.x))

		#Filter stuff
		self.filtord = 3

		#Filtering AC mains
		fc = 50
		f_l = (fc-2)*2/self.Fs
		f_h = (fc+2)*2/self.Fs
		self.b, self.a = scisig.butter(self.filtord, [f_l, f_h], btype='bandstop', output='ba')
		self.zi = scisig.lfilter_zi(self.b, self.a)

		#Full wave rectifier inteference
		fc1 = 100
		f_l1 = (fc1-2)*2/self.Fs
		f_h1 = (fc1+2)*2/self.Fs
		self.b1, self.a1 = scisig.butter(self.filtord, [f_l1, f_h1], btype='bandstop', output='ba')
		self.zi1 = scisig.lfilter_zi(self.b1, self.a1)

		#High pass for baseline drift
		fc2 = 0.2*2/self.Fs
		self.b2, self.a2 = scisig.butter(self.filtord, fc2, btype='highpass', output='ba')
		self.zi2 = scisig.lfilter_zi(self.b2, self.a2)

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.update)

		self.traces = dict()
		self.traces = dict()
		self.app = QtGui.QApplication(sys.argv)
		super(Window, self).__init__()
		self.setGeometry(50, 50, 1000, 700)
		self.setWindowTitle("Test")
		self.setWindowIcon(QtGui.QIcon('logo.png'))
		self.home()

		extractAction = QtGui.QAction("&Quit", self)
		extractAction.setShortcut("Ctrl+Q")
		extractAction.setStatusTip('Exit..')
		extractAction.triggered.connect(self.close_application)

		action2 = QtGui.QAction("&Change Title", self)
		action2.setStatusTip("Change the title...")
		action2.triggered.connect(self.changeTest)

		self.statusBar()

		mainMenu = self.menuBar()
		mainMenu.setNativeMenuBar(False) 
		fileMenu = mainMenu.addMenu("&File")
		fileMenu.addAction(extractAction)
		editMenu = mainMenu.addMenu("&Edit")
		editMenu.addAction(action2)

		self.Graphs = QtGui.QWidget()
		self.layout = QtGui.QVBoxLayout()
		self.RawSig = pg.PlotWidget(title="Raw Signal")
		self.FFT = pg.PlotWidget(title="FFT")
		self.layout.addWidget(self.RawSig)
		self.layout.addWidget(self.FFT)
		self.Graphs.setLayout(self.layout)
		self.setCentralWidget(self.Graphs)

		self.traces['sin'] = self.RawSig.plot(pen='y')
		self.traces['FFT'] = self.FFT.plot(pen='y')

	def home(self):

		startRec = QtGui.QAction(QtGui.QIcon('greenlight.png'), "Start Recording", self)
		startRec.triggered.connect(self.startRecording)

		stopRec = QtGui.QAction(QtGui.QIcon('redlight.png'), "Stop Recording", self)
		stopRec.triggered.connect(self.stopRecording)

		self.toolBar = self.addToolBar("ToolBar")
		self.toolBar.addAction(startRec)
		self.toolBar.addAction(stopRec)

		self.show()


	def changeTest(self):
		self.setWindowTitle("Change Test")

	def update(self):
		#s = sin(2 * pi * self.time * self.freq)
		array = np.zeros(self.winSize)
		for i in range(self.winSize):

			try:
				temp = float(self.serData.readLine().strip())
			except:
				temp = 0
			if temp >= 1024.0:
				temp = 1024.0

			array[0] = temp
			array = np.roll(array, 1)
		array, zi = scisig.lfilter(self.b, self.a, array, zi=self.zi)
		self.zi = zi

		array, zi1 = scisig.lfilter(self.b1, self.a1, array, zi=self.zi1)
		self.zi1 = zi1

		array, zi2 = scisig.lfilter(self.b2, self.a2, array, zi=self.zi2)
		self.zi2 = zi2

		self.t[:self.winSize] = array[:]
		self.t = np.roll(self.t, self.winSize)
		self.trace("sin",self.x,self.t)
		self.trace("FFT",spfft.fftfreq(len(self.x), self.T),np.absolute(spfft.fft(self.t)))
		#self.freq += 0.01
		#self.time += 0.01

	def startRecording(self):
		if self.started == 0:
			print("Started recording...")
			self.started = 1
			self.timer.start(2)
			self.start()
			self.serData.open()

	def stopRecording(self):
		if self.started == 1:
			print("Stopped recording...")
			self.started = 0
			self.timer.stop()
			self.serData.exit()

	def close_application(self):
		choice = QtGui.QMessageBox.question(self, 'Confirm..', "Quit?",
			QtGui.QMessageBox.No | QtGui.QMessageBox.Yes)

		if choice == QtGui.QMessageBox.Yes:
			sys.exit()

		else:
			pass

	def start(self):
		if (sys.flags.interactive == 1) or not hasattr(QtCore, 'PYQT_VERSION'):
			sys.exit()

	def trace(self, name, dataset_x,dataset_y):
		if name in self.traces:
			self.traces[name].setData(dataset_x,dataset_y)




if __name__ == '__main__':

	GUI = Window()
	sys.exit(GUI.app.exec_())