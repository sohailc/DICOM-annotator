This program load an image file in PNG, JPG, BMP or DICOM format and 
displays the contents. Simple GUI elements let the user add annotation 
and save the annotations to a seperate file. 

DICOM stands for Digital Imaging and Communications in Medicine and 
is the standard format in medical imaging. 

A row of buttons at the bottom of the window should let the user open
a DICOM file. If an annotation file exists (DICOM file name + "_annotations")
the annotation file will also be loaded and displayed. 

Any annotation made should be saved with the "save annotations for file"
button. 

As of this version, the user can only create boxes, lines and text to 
annotate a file. It is also not possible yet to modify the annotations 
once made.

Dependencies:

	* python
	* python-dicom
	* python-wxgtk
	* python-matplotlib
	
