""" 
Saves an iteration of the open file and optionally exports a render script.
To work, the file name must be formatted as "name_v001.ext".
"""

import maya.cmds as cmds
from functools import partial
import os

def splitName(fileName):
	# Converts a file name into a list consisting of its base name [0], its version [1], and its extension [2].
	output = ["0", "1", "2"]
	# Split the extension. Place it in the list.
	extensionSplit = fileName.rsplit('.', 1)
	output[2] = extensionSplit[1]
	# Split the version. Place it in the list.
	versionSplit = extensionSplit[0].rsplit('_', 1)
	output[1] = versionSplit[1]
	# Add the base name to the list.
	output[0] = versionSplit[0]
	# Return the list.
	return output
	
def updateVersion(version):
	# Iterates the version number up and returns it as a string.
	# Strip the "v" out of the version.
	removeVersion = version.strip("v")
	# Save the padding length, then strip away the leading zeroes.
	padding = len(removeVersion)
	removePadding = removeVersion.lstrip("0")
	# Iterate up one version.
	version = int(removePadding) + 1
	# Replace the "v" and the leading zeroes.
	output = ""
	while len(output) < padding - len(str(version)):
		output = output + "0"
	output = "v" + output + str(version)
	# Return the version as a string.
	return output
	
def cleanPath(scenePath):
	# This function reformats a path so the command line can read it.
	# Breakdown the file path into components.
	scenePath = scenePath.strip()
	pathComponents = scenePath.split("/")
	updatedComponents = []
	
	# If spaces exist in component names, surround them with quotations.
	for component in pathComponents:
		if component.find(" ") > -1:
			outComponent = '"' + component + '"/'
		else: 
			outComponent = component + '/'
		updatedComponents.append(outComponent)
	
	# Assemble a new string and return.
	output = "".join(updatedComponents)
	return output
	
def getCameras():
	# Returns a list of cameras with their respective frame ranges.
	# First get a list of all the cameras in the scene.
	allCameras = cmds.ls(cameras = True)
	renderCameras = []
	
	for each in allCameras:
		startFrame = 0
		endFrame = 0
		
		# Check to see if the camera is renderable.
		if cmds.getAttr(each +".renderable"):
			# Check to see if the camera has custom frame range attributes.
			if cmds.attributeQuery('startFrame', node = each, exists = True) == False:
				# If not, create custom attributes and set them to the default render globals.
				startFrame = cmds.getAttr('defaultRenderGlobals.startFrame')
				endFrame = cmds.getAttr('defaultRenderGlobals.endFrame')
				
				print ("\nCreating frame range attributes for "+ each +".\n")
				cmds.addAttr(each, longName = 'startFrame', attributeType = 'long')
				cmds.addAttr(each, longName = 'endFrame', attributeType = 'long')
				cmds.setAttr(each +".startFrame", startFrame)
				cmds.setAttr(each +".endFrame", endFrame)
		
			startFrame = cmds.getAttr(each +".startFrame")
			endFrame = cmds.getAttr(each +".endFrame")	

			# Get the transform for each camera.
			cameraTransform = cmds.listRelatives(each, parent = True)
			
			# Add the final render information to the output list.
			renderCameras.append("-cam "+ cameraTransform[0] +" -s "+ str(startFrame) +" -e "+ str(endFrame))
	return renderCameras
	
def getLayers():
	# Returns a list containing the scene's render layers.
	baseRenderLayers = cmds.listConnections('renderLayerManager.renderLayerId')
	activeLayers = []
	
	# Iterate through the list of layers. Determine which are renderable.
	for each in baseRenderLayers:
		if cmds.getAttr(each +".renderable"):
			# If renderable, add the current layer and its cameras to the render text.
			cmds.editRenderLayerGlobals(currentRenderLayer = each)
			cameraList = getCameras()
			
			for eachCamera in cameraList:
				activeLayers.append("-rl "+ each + " " + eachCamera + " ")
		
	baseRenderLayers = []
	cmds.editRenderLayerGlobals(currentRenderLayer = 'defaultRenderLayer')	
	return activeLayers
	
def getResolution():
	# Returns the scene's resolution settings.
	x = cmds.getAttr('defaultResolution.width')
	y = cmds.getAttr('defaultResolution.height')
	output = "-x "+ str(x) +" -y "+ str(y) +" "
	return output
	
def getHeader(operatingSystem):
	# Adds a header for bash.
	header = ""
	if (operatingSystem == "mac"):
		header = "#!/bin/bash\n"
	else:
		header = "\n"
	return header
	
def saveIteration():
	# Saves a new version of the open file.
	# Get the file path and the current file name.
	filePath = cmds.file(query = True, expandName = True).strip(cmds.file(sceneName = True, shortName = True, query = True))
	fileName = splitName(cmds.file(sceneName = True, shortName = True, query = True))
	
	# Iterate the version up.
	fileName[1] = updateVersion(fileName[1])
	newFileName = fileName[0] +"_"+ fileName[1] +"."+ fileName[2]
	
	# Save the new file.
	cmds.file (rename = newFileName)
	cmds.file (save=True)
	return newFileName
	
def exportScript():
	# Get the operating system.
	operatingSystem = cmds.about (os = True)
	extension = ""
	
	if operatingSystem == "mac":
		extension = ".command"
	elif operatingSystem == "nt" or operatingSystem == "win64":
		operatingSystem = "windows"
		extension = ".bat"
	elif operatingSystem == "linux" or operatingSystem == "linux64":
		operatingSystem = "linux"
		extension = ".sh"
	else:
		print "Invalid operating system."
		
	# Get the scene path.
	scenePath = cleanPath(cmds.file(query = True, expandName = True).strip(cmds.file(sceneName = True, shortName = True, query = True)).rstrip("/"))
	
	# Get the file path.
	filePath = scenePath + cmds.file(sceneName = True, shortName = True, query = True)

	# Get the renderer path.
	rendererPath = cleanPath(os.getenv("MAYA_LOCATION")) + "bin/render"
	
	# Get the project path.
	projectPath = cleanPath(cmds.workspace(fullName = True))
	project = "-proj " + projectPath + " "
	
	# Get the script path and file name.
	baseList = splitName(cmds.file(sceneName = True, shortName = True, query = True))
	base = baseList[0] +"_"+ baseList[1]
	scriptName = base + extension
	scriptPath = cmds.file(query = True, expandName = True).strip(cmds.file(sceneName = True, shortName = True, query = True)) + scriptName
	
	# Get the header.
	header = getHeader(operatingSystem)
	
	# Get the scene resolution.
	resolution = getResolution()
	
	# Get the scene render layers.
	renderLayers = getLayers()
	
	# Create the list of render commands.
	renderCommands = []
	
	for eachLayer in renderLayers:
		renderCommands.append(rendererPath + " " + project + " " + eachLayer + resolution + filePath +"\n")
		
	# Create the file and start writing.	
	batchFile = open(scriptPath, 'w')
	batchFile.write(header)
	for eachLayer in renderCommands:
		batchFile.write(eachLayer)
		batchFile.write("\n")
	batchFile.close
	
	return scriptName
	
def batchAndSaveExecute(type, *args):
	# Check to see if the file is being saved or the script is being exported.
	save = cmds.checkBox("saveBox", query = True, value = True)
	batch = cmds.checkBox("batchBox", query = True, value = True)
		
	# Execute helper functions to export the script or save a new version.
	if batch:
		scriptName = exportScript()		
	if save:
		saveName = saveIteration()
	
	# Provide feedback for successes or failures.
	warning = ""
	if save == True and batch == False:
		warning = "Saved '"+ saveName +"'."
	elif save == False and batch == True:
		warning = "Exported '"+ scriptName +"'."
	elif save == True and batch == True:
		warning = "Batch script exported and version saved."
	else:
		warning = "This will do nothing."
	
	cmds.textField ("warningField", edit = True, text = warning)
	
def batchAndSave():
	batchAndSaveWindow()
	
def batchAndSaveWindow():
	if cmds.window ("batchSaveWindow", exists = True):
		cmds.deleteUI("batchSaveWindow")
		
	width = 250
	
	window = cmds.window("batchSaveWindow", title = "Batch 'n' Save", titleBar = True, width = width, sizeable = True, resizeToFitChildren = False)
		
	cmds.frameLayout ( labelVisible = 0, marginWidth = 5, marginHeight = 5 )
	columnLayout1 = cmds.columnLayout ( adjustableColumn = False )
	cmds.text("Exports a batch render script for the active\nrender layers and saves a version of the file.", align = "left")
	cmds.separator(h=10, st='in')
	cmds.checkBox("batchBox", label = "Export render script", value = True)
	cmds.checkBox("saveBox", label = "Save new version", value = True)
	cmds.separator(h=10, st='in')
	cmds.setParent('..')	
	rowLayout1 = cmds.rowLayout (numberOfColumns = 3, parent = columnLayout1)
	cmds.button(label = "Execute", width = width - 20, height = 40, command = partial(batchAndSaveExecute))
	cmds.setParent('..')
	cmds.separator(h=10, st='in')
	cmds.textField ("warningField", width = width - 20, height = 20, text = "", editable = False)
	cmds.showWindow(window)
	
batchAndSaveWindow()