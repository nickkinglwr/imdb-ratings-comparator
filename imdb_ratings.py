import sys
import imdb
import multiprocessing.dummy
from PySide import QtGui
from PySide import QtCore


__appname__ = "Imdb Ratings"

class MWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MWindow, self).__init__(parent)

        self.seriesNames = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle(__appname__)
        self.textBox = QtGui.QTextBrowser()
        self.textBox.setText("Enter series to process in line edit below")
        self.lineEdit = QtGui.QLineEdit()
        self.multiCheck = QtGui.QCheckBox("Process multiple series (Put each series in \"\")")
        self.threadBox = QtGui.QSpinBox()
        self.threadBox.setRange(1,32)
        self.threadBox.setValue(8)
        self.threadsLab = QtGui.QLabel("Thread count:")
        self.statusLab = QtGui.QLabel("")
        self.parser = "lxml"
        self.opt_dialog = optDialog(self)


        self.menuB = self.menuBar()
        self.fileMenu = self.menuB.addMenu("&File")
        self.editMenu = self.menuB.addMenu("&Edit")
        self.optMenu = self.menuB.addMenu("&Options")

        self.cWidget= QtGui.QWidget()

        self.saveAct = QtGui.QAction(QtGui.QIcon.fromTheme("document-save"), "&Save", self)
        self.saveAct.setShortcut("Ctrl+S")
        self.saveAct.setToolTip("Save output to .txt file")
        self.saveAct.triggered.connect(self.saveOut)

        self.openAct = QtGui.QAction(QtGui.QIcon.fromTheme("document-open"), "&Open", self)
        self.openAct.setShortcut("Ctrl+O")
        self.openAct.setToolTip("Open .txt containg show names to find ratings")
        self.openAct.triggered.connect(self.openOut)

        self.optionAct = QtGui.QAction(QtGui.QIcon.fromTheme(""), "&Options", self)
        self.optionAct.setShortcut("Ctrl+Shift+O")
        self.optionAct.setToolTip("Open options dialog")
        self.optionAct.triggered.connect(self.openOptions)

        self.copyAct = QtGui.QAction(QtGui.QIcon.fromTheme("edit-copy"), "&Copy", self)
        self.copyAct.setShortcut("Ctrl+C")
        self.copyAct.setToolTip("Copy selected text to clipboard")
        self.copyAct.triggered.connect(lambda: self.textBox.copy())

        self.pasteAct = QtGui.QAction(QtGui.QIcon.fromTheme("edit-paste"), "&Paste", self)
        self.pasteAct.setShortcut("Ctrl+V")
        self.pasteAct.setToolTip("Paste into line edit")
        self.pasteAct.triggered.connect(lambda: self.lineEdit.paste())

        self.SAAct = QtGui.QAction(QtGui.QIcon.fromTheme(""), "&Select All", self)
        self.SAAct.setShortcut("Ctrl+A")
        self.SAAct.setToolTip("Select All text in output")
        self.SAAct.triggered.connect(lambda: self.textBox.selectAll())

        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.openAct)
        self.editMenu.addAction(self.copyAct)
        self.editMenu.addAction(self.pasteAct)
        self.editMenu.addAction(self.SAAct)
        self.optMenu.addAction(self.optionAct)

        self.resize(1920,1080)

        self.lineEdit.returnPressed.connect(self.singleSearch)
        self.setCentralWidget(self.cWidget)

        layout = QtGui.QGridLayout()
        layout.addWidget(self.textBox,0,0)
        layout.addWidget(self.lineEdit,1,0)
        layout.addWidget(self.multiCheck,2,0)
        layout.addWidget(self.threadsLab,2,2)
        layout.addWidget(self.threadBox,2,3)
        layout.addWidget(self.statusLab,3,0)
        layout.setRowStretch(0, 3)
        self.cWidget.setLayout(layout)



    def saveOut(self):
        try:
            dir = '.'
            saveFile = QtGui.QFileDialog.getSaveFileName(self, __appname__ + "Save", dir=dir, filter="Text files (*.txt)")
            with open(saveFile[0],'w') as f:
                f.write(self.textBox.toPlainText())
            self.statusLab.setText("Saved output to file {}".format(saveFile[0]))
        except:
            self.statusLab.setText("Error saving file")

    def openOut(self):
        try:
            dir = '.'
            openFile = QtGui.QFileDialog.getOpenFileName(self, __appname__ + "Open", dir=dir, filter="Text files (*.txt)")
            with open(openFile[0], 'r') as f:
                self.seriesNames = [i.strip().split() for i in f]
            self.statusLab.setText("Open series from file {}".format(openFile[0]))
        except:
            self.statusLab.setText("Error opening file")

    def openOptions(self):
        self.opt_dialog.exec_()
        print(self.parser)

    def singleSearch(self):
        if self.multiCheck.isChecked():
            self.searchMulti()
            return
        self.statusLab.setText("Processing {} ratings...".format(self.lineEdit.text()))
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        rating = imdb.ImdbRatings(self.lineEdit.text(), parser=self.parser, threads=int(self.threadBox.text()))

        self.textBox.clear()
        try:
            self.textBox.setText(rating.get_ratings())
            self.statusLab.setText("Done processing {} ratings.".format(self.lineEdit.text()))
            QtGui.QApplication.restoreOverrideCursor()
        except Exception as e:
            self.statusLab.setText("Could not process ratings. {}".format(e))
            QtGui.QApplication.restoreOverrideCursor()


    def searchMulti(self):
        self.statusLab.setText("Processing multiple series...")

        if len(self.seriesNames) == 0:
            self.seriesNames = self.lineEdit.text().split("\"")
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        results = []
        series = []
        pool = multiprocessing.dummy.Pool(int(self.threadBox.text()))

        self.textBox.clear()

        for x in self.seriesNames:
            if x != '' and x != ' ':
                i = imdb.ImdbRatings(x, parser=self.parser, threads=int(self.threadBox.text()))
                series.append(i)

        try:
            results = pool.map(lambda x: x.get_ratings(), series)
            QtGui.QApplication.restoreOverrideCursor()
        except Exception as e:
            self.statusLab.setText("Could not process ratings (Make sure each series is in seperate \" \"). {}".format(e))
            QtGui.QApplication.restoreOverrideCursor()

        for i in results:
            self.textBox.append(i + "\n\n\n")

class optDialog(QtGui.QDialog):
    def __init__(self, mainWin, parent = None):
        super(optDialog, self).__init__(parent)

        self.initUI(mainWin)

    def initUI(self, mainWin):
        self.optParserLab = QtGui.QLabel("Other parser: ")
        self.optParserComboBox = QtGui.QComboBox()
        self.optParserComboBox.addItem("lxml")
        self.optParserComboBox.addItem("html.parser")
        self.optParserComboBox.addItem("html5lib")
        self.optParserComboBox.setCurrentIndex(0)
        self.mainWindow = mainWin

        self.setWindowTitle("Options")

        layout = QtGui.QGridLayout()
        layout.addWidget(self.optParserLab, 0, 0)
        layout.addWidget(self.optParserComboBox, 0,1)
        self.setLayout(layout)

        self.optParserComboBox.currentIndexChanged.connect(self.setParser)

    def setParser(self):
        self.mainWindow.parser = self.optParserComboBox.currentText()
        return self.optParserComboBox.currentIndex()

app = QtGui.QApplication(sys.argv)
mainWindow = MWindow()
mainWindow.show()

app.exec_()