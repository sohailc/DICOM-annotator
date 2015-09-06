"""
This program load a DICOM file and displays the contents. Simple GUI 
elements let the user add annotation and save the annotations to a
seperate file 

Author: Sohail Chatoor (6 December 2015)
"""


from matplotlib import pyplot as plt
from matplotlib.widgets import Button
import wx # 3.0
import re
import dicom
import os

class DICOMViewer(object):
	
	def __init__(self):
		
		# We will use matplotlib to show the DICOM file data
		self.fig, self.ax = plt.subplots()
		plt.subplots_adjust(bottom=0.2)
		self.canvas = self.fig.canvas
		
		# We will be able to annotate the DICOM file with 
		# lines, boxes and text, which will be shown in red
		drawColor = "r"
		self.lineDrawer = LineDrawer(self, drawColor)
		self.rectDrawer = RectDrawer(self, drawColor)
		self.textDrawer = TextDrawer(self, drawColor)
		self.currentDrawer = None
		
		# The self.buttons dictionary stors the button 
		# text as the keys and the call back function as the value
		# Buttons in the GUI will enable us to draw lines, boxes and text
		# Some buttons also allow us to open a DICOM file and save the
		# annotations
		self.buttons = {"lines": self.lineDrawer, 
						"rectangles": self.rectDrawer, 
						"text": self.textDrawer, 
						"open dicom file": self.openDICOMFile, 
						"save annotations to file": self.saveAnnotationsToFile} 
		
		self.makeGUIButtons()
		
		# We also have shortcut keys 
		self.shortcutKeyMap = {	"ctrl+l": "lines",
								"ctrl+r": "rectangles", 
								"ctrl+t": "text"}
		
		self.canvas.mpl_connect('key_press_event', self.keyPress)
		
		self.annotationFile = None
		self.dicomFile = None
		
		plt.show()
	
	def makeGUIButtons(self):
		
		# Loop though the self.buttons dictionary and create the buttons
		buttonPosX = 0.01
		self.buttonObjects = []
		for buttonText in self.buttons:
			
			# the length of a button is dependant on the amount of text
			# it displays
			bLen = 0.05*(len(buttonText)-4)/(6.0)+0.1
			
			axButton = plt.axes([buttonPosX, 0.05, bLen, 0.075])
			button = Button(axButton, buttonText)
			buttonCallback = self.buttons[buttonText]
			button.on_clicked(buttonCallback)
			self.buttonObjects.append(button)
			buttonPosX += bLen+0.01
	
	def openDICOMFile(self, event):
		
		self.dicomFile = self.openDICOMFileDialog()
		
		if not self.dicomFile: # If the user cancels...
			return
		
		try: # make sure the user selects a valid file
			ds = dicom.read_file(self.dicomFile)
		except dicom.filereader.InvalidDicomError:
			print "error, file not a DICOM file"
			return
			
		self.ax.imshow(ds.pixel_array, interpolation="nearest", cmap=plt.gray())
		
		# the following lines seem strange, this this allows us to 
		# draw things on the axes without the limits changing 
		self.ax.set_xlim(self.ax.get_xlim())
		self.ax.set_ylim(self.ax.get_ylim())
		
		self.annotationFile = self.dicomFile+ "_annotations"
		
		# if an annotation file exists, load it
		if os.path.exists(self.annotationFile):
			self.loadAnnotationsFromFile(self.annotationFile)
	
	def openDICOMFileDialog(self):
		
		app = wx.App(None)
		style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		dialog = wx.FileDialog(None, 'Open', wildcard="*", style=style)
		if dialog.ShowModal() == wx.ID_OK:
			path = dialog.GetPath()
		else:
			path = None
		dialog.Destroy()
		return path
		
	def keyPress(self, event):
		
		key = event.key
		
		if not key in self.shortcutKeyMap: # The user pressed a key 
			# which is not in the shortcuts list
		
			if not self.currentDrawer:
				return
			
			self.currentDrawer.handleKey(key) # if a drawer is active
			# let the drawer handle the key input. E.g. if the text 
			# drawer is active, the key will be printed on the screen
		
		else: # Perform the action of the shortcut key
			
			drawerName = self.keyMap[key]
			self.currentDrawer = self.drawerObjects[drawerName]
			self.currentDrawer()
	
	def saveAnnotationsToFile(self, event):
		
		if self.dicomFile == None: # nothing to do if no DICOM file is 
			# loaded
			return
		
		# If a drawer is active, disconnect it first. This will cause it 
		# to save recent modifications
		if self.currentDrawer:
			self.currentDrawer._disconnect()
		
		# All drawers have a dictionary of objects with the fields 
		# "objectType", "text", "x0", "y0", "x1", "y1". What these 
		# fields mean is dependent on the particular drawer. 
		# When we reload the data, the data is transformed back into 
		# a dictionary from text and given to the "drawData" method
		# of the appropriate drawer
		ln = "objectType: {objectType}, text: {text}, x0: {x0}, y0: {y0}, x1: {x1}, y1: {y1}"
		
		with open(self.annotationFile, "w") as fh:
			
			# Loop over all the buttons in the GUI
			for drawerName in self.buttons:
				
				drawerObject = self.buttons[drawerName]
				
				# The buttons "load DICOM file" and 
				# "save annotations" do not have object data
				if not hasattr(drawerObject, "objectData"):
					continue
				
				# Loop over each object element and save as a line
				# in the annotation file. 
				for dataObject in drawerObject.objectData:
					dataObject["objectType"] = drawerName
					textToPrint = ln.format(**dataObject) + "\n"
					fh.write(textToPrint)
	
	def loadAnnotationsFromFile(self, fileName):
		
		# We read the annoation file line by line and use regular
		# expressions to parse the line. 
		dataFields = ["objectType", "text", "x0", "y0", "x1", "y1"]
		dataTypes = ["(\w*)", "(|.+)"] + 4*["(.*)"]
		
		matchString = ", ".join(["%s: %s" % (f,t) for f,t in zip(dataFields, dataTypes)])
		
		with open(fileName, "r") as fh:
			
			for line in fh:
				
				if line.strip() == "":
					continue
				
				result = re.search(matchString, line)
				parts = result.groups()
				
				values = []
				for value in parts:
					
					if unicode(value).isnumeric():
						value = float(value)
					
					values.append(value)
					
				dataLine = dict(zip(dataFields, values))
				
				# Find out which drawer printed the line the annotation
				# file and call the that drawer with the appropriate
				# data. This will recreate the annotations
				self.buttons[dataLine["objectType"]].drawData(dataLine)
					
# We have objects which draw different things on the canvas 
# (e.g. LineDrawer). Each of these objects inherit from the 
# DrawerObject class. Some methods of the DrawerObject class
# are deliberately left as stubs, which will be implemented 
# fully by the inheriting classes

class DrawerObject(object):
	def __init__(self, viewer, color):
		
		self.viewer = viewer
		self.fig = viewer.fig
		self.ax = viewer.ax
		self.canvas = self.fig.canvas
		self.color = color
		self.objectData = []
		self.currentLine = None
		self.currentText = None
		self.background = None
		self.keyPressed = False
		
		self.x0 = None
		self.y0 = None
		
		# The following are callback functions for mouse events
		self.cmlp = None # cmlp = connection mouse left press
		self.cmm = None # cmm = connection mouse move
		self.cmlr = None # cmlr = connection mouse left release
		
	def __call__(self, event=None):
		
		# If a previous drawer object is still active, disconnect that 
		# drawer object first. This way, only the current drawer will 
		# react to mouse events
		if self.viewer.currentDrawer != None:
			self.viewer.currentDrawer._disconnect()
		
		self.viewer.currentDrawer = self
		
		# Make the current object responsive to mouse events
		self.cmlp = self.canvas.mpl_connect('button_press_event', self.mouseLeftPress)
		self.cmm = self.canvas.mpl_connect('motion_notify_event', self.mouseMove)
		self.cmlr = self.canvas.mpl_connect('button_release_event', self.mouseLeftRelease)
	
	def _disconnect(self):
		
		self.canvas.mpl_disconnect(self.cmlp)
		self.canvas.mpl_disconnect(self.cmm)
		self.canvas.mpl_disconnect(self.cmlr)
	
	# The following functions are implemented by inheriting classes
	def mouseLeftPress(self, event):
		pass
	
	def mouseMove(self, event):
		pass
	
	def mouseLeftRelease(self, event):
		pass
	
	def handleKey(self, key):
		pass
	
	def drawData(self, data):
		pass

class LineDrawer(DrawerObject): # Draw lines on the canvas
	
	def mouseLeftPress(self, event):
		
		if event.inaxes!=self.ax: return  # Make sure the mouse is on the 
		# main axis before processing this function
		self.keyPressed = True 
		
		self.x0 = event.xdata
		self.y0 = event.ydata
		self.currentLine, = self.ax.plot([self.x0], [self.y0], self.color)
		
		self.currentLine.set_animated(True)
		self.canvas.draw()
		self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        
		self.ax.draw_artist(self.currentLine)
		self.canvas.blit(self.ax.bbox)
	
	def mouseMove(self, event):
		
		if event.inaxes!=self.ax: return # Make sure the mouse is on the 
		# main axis before processing this function
		if not self.keyPressed: return # Only process this function when
		# the mouse key is pressed
		
		x = event.xdata
		y = event.ydata
		self.currentLine.set_data([self.x0,x], [self.y0,y])
		
		self.canvas.restore_region(self.background)
		self.ax.draw_artist(self.currentLine)

		self.canvas.blit(self.ax.bbox)
	
	def mouseLeftRelease(self, event):
		
		if event.inaxes!=self.ax: return # Make sure the mouse is on the 
		# main axis before processing this function
		self.keyPressed = False
		
		x = event.xdata
		y = event.ydata
		
		# When the user releases the key, store the line data in the 
		# object data array
		ldata = {"x0": self.x0,"y0": self.y0,"x1": x,"y1": y, "text":""}
		self.objectData.append(ldata)
		
		self.currentLine.set_animated(False)
		self.background = None

		self.canvas.draw()
	
	def drawData(self, ldata):
		# This method is called when an annotation file is reloaded 
		# Put the object data back in the memory
		self.objectData.append(ldata)
		# and redraw the line
		x0 = ldata["x0"]
		y0 = ldata["y0"]
		x1 = ldata["x1"]
		y1 = ldata["y1"]
		
		self.ax.plot([x0,x1],[y0,y1],self.color)
		self.canvas.draw()
		
class RectDrawer(DrawerObject): # Draw boxes on the canvas
	
	def mouseLeftPress(self, event):
		
		if event.inaxes!=self.ax: return # Make sure the mouse is on the 
		# main axis before processing this function
		self.keyPressed = True
		
		self.x0 = event.xdata
		self.y0 = event.ydata
		
		line1, = self.ax.plot([self.x0], [self.y0], self.color)
		line2, = self.ax.plot([self.x0], [self.y0], self.color)
		line3, = self.ax.plot([self.x0], [self.y0], self.color)
		line4, = self.ax.plot([self.x0], [self.y0], self.color)
		
		self.currentLine = [line1, line2, line3, line4]
		
		self.canvas.draw()
		self.background = self.canvas.copy_from_bbox(self.ax.bbox)
		
		for line in self.currentLine:
			line.set_animated(True)
			self.ax.draw_artist(line)

		self.canvas.blit(self.ax.bbox)

	def mouseMove(self, event):
		
		if event.inaxes!=self.ax: return # Make sure the mouse is on the 
		# main axis before processing this function
		if not self.keyPressed: return # Only process this function when
		# the mouse key is pressed
		
		x = event.xdata
		y = event.ydata
		
		line1, line2, line3, line4 = self.currentLine
		
		self.canvas.restore_region(self.background)
		
		# Draw the four sides of the box
		line1.set_data([self.x0, x], [self.y0, self.y0])
		self.ax.draw_artist(line1)
		
		line2.set_data([x, x], [self.y0, y])
		self.ax.draw_artist(line2)
		
		line3.set_data([x, self.x0], [y, y])
		self.ax.draw_artist(line3)
		
		line4.set_data([self.x0, self.x0], [y, self.y0])
		self.ax.draw_artist(line4)
		
		self.canvas.blit(self.ax.bbox)
	
	def mouseLeftRelease(self, event):
		
		if event.inaxes!=self.ax: return # Make sure the mouse is on the 
		# main axis before processing this function
		self.keyPressed = False
		
		x = event.xdata
		y = event.ydata
		
		# When the user releases the key, store the line data in the 
		# object data array
		rdata = {"x0": self.x0,"y0": self.y0,"x1": x,"y1": y, "text":""}
		self.objectData.append(rdata)
		
		for line in self.currentLine:
			line.set_animated(False)
			
		self.background = None
		self.canvas.draw()
	
	def drawData(self, rdata):
		# This method is called when an annotation file is reloaded 
		# Put the object data back in the memory
		self.objectData.append(rdata)
		
		x0 = rdata["x0"]
		y0 = rdata["y0"]
		x1 = rdata["x1"]
		y1 = rdata["y1"]
		
		self.ax.plot([x0,x1],[y0,y0],self.color)
		self.ax.plot([x1,x1],[y0,y1],self.color)
		self.ax.plot([x1,x0],[y1,y1],self.color)
		self.ax.plot([x0,x0],[y1,y0],self.color)
		self.canvas.draw()

class TextDrawer(DrawerObject): # Draw text on the canvas
	
	def _saveDefaultPltParams(self):
		# By default, matplotlib has some shortcut keys which will 
		# interfere with typing text. Save the matplotlib parameters,
		# replace them temporarily by an empty string and restore them
		# after the user is done typing text
		
		self.defaultPltParams = dict()
		
		for pltParam in plt.rcParams:
			if "keymap" in pltParam:
				self.defaultPltParams[pltParam] = plt.rcParams[pltParam]
				plt.rcParams[pltParam] = ""
	
	def _restoreDefaultPltParams(self):
		
		for pltParam in self.defaultPltParams:
			plt.rcParams[pltParam] = self.defaultPltParams[pltParam]
	
	def _disconnect(self):
		# We have a disconnect routine which is slightly different then
		# other drawer objects. Simulate an "enter" key press do let 
		# other parts of the program know we are done typing text. 
		self.handleKey("enter")
		DrawerObject._disconnect(self)
	
	def mouseLeftPress(self, event):
		
		if event.inaxes!=self.ax: return
		
		self._saveDefaultPltParams()
		
		self.x0 = event.xdata
		self.y0 = event.ydata
		# the "|" represents a carat
		self.currentText = self.ax.text(self.x0, self.y0,"|", color=self.color)
		self.canvas.draw()
	
	def handleKey(self, key):

		done = False
		
		if self.currentText == None:
			return
		
		currentTextStr = self.currentText.get_text().strip("|")
		
		if len(key) > 1:
			
			if key == "backspace":
				textToSet = currentTextStr[:-1] + "|"
			elif key == "enter":
				self._restoreDefaultPltParams()
				textToSet = currentTextStr
				done = True
			else:
				return
		else:
			textToSet = currentTextStr + key + "|"
		
		self.currentText.set_text(textToSet)
		self.canvas.draw()
		
		if done:
			# Save the text daata in the objectData dictionary
			tData = {"x0": self.x0, "y0": self.y0, "text": textToSet, "x1":None, "y1":None}
			self.objectData.append(tData)
			self.currentText = None
		
	def drawData(self, tdata):
		
		# This method is called when an annotation file is reloaded 
		# Put the object data back in the memory
		self.objectData.append(tdata)
		
		x0 = tdata["x0"]
		y0 = tdata["y0"]
		text = tdata["text"]
		
		self.ax.text(x0, y0, text, color=self.color)
		self.canvas.draw()

def main():
	viewer = DICOMViewer()
	
if __name__ == "__main__":
	main()
