import maya.cmds as cmds

class RibbonSpine(object):
	
	def createRibbonSpine(self, name = "ribbonSpine", joints = 5):
		self.name = name
		self.joints = joints
		
		# Creates a hierarchy of groups to store our rig.
		self.masterGroup = cmds.group (name = "%s_MST_GRP" % self.name, empty = True)
		self.moveGroup = cmds.group (name = "%s_MOVE_GRP" % self.name, empty = True, parent = self.masterGroup)
		self.noMoveGroup = cmds.group (name = "%s_NOMOVE_GRP" % self.name, empty = True, parent = self.masterGroup)
		
		# Create a NURBS plane that matches the distance between the two locators.
		self.plane = self.createPlane()
		self.blendOffset = (self.distance * (1.0 / self.joints)) * 2
		
		# Duplicate the plane, shift it sideways, and apply it as a blend shape to the original.
		self.planeBlend = self.createPlaneBlend()
		self.planeBlendDeformer = cmds.blendShape (self.planeBlend, self.plane, weight = (0, 1), name = self.name +"_DFM")
		
		# Place a follicle on each patch on the original plane. Then parent joints beneath the follicles.
		self.follicles = self.createFollicles()
		self.bindJoints = self.createJoints()
		
		# Set up joints and curves as controls.
		self.controlCurves = self.createControlCurves()
		
		# Apply a wire deformer to the blend shape.
		self.wireDeformerCurve = cmds.curve(degree = 2, point = [(self.blendOffset, (self.distance/2) * -1, 0), (self.blendOffset, 0, 0), (self.blendOffset, (self.distance/2),0 )], name = "%s_WIRE_CRV" % self.name)
		self.planeWireDeformer = cmds.wire(self.planeBlend, wire = self.wireDeformerCurve, groupWithBase = False, envelope = 1.0, crossingEffect = 0, localInfluence = 0, dropoffDistance = [0, 20])
		
		# Apply clusters to the wire deformer and connect them to the control curves.
		self.clusterDeformers = self.createClusterDeformers()
		
		# A twist deformer allows for better rotation on the X axis.
		# Add a switch to allow squash and stretch.
		self.twistDeformer = self.createTwistDeformer()
		self.createStretchDeformer()
		
		# Initial clean-up. Move objects into their respective groups.
		self.parentObject(self.plane, self.moveGroup)
		self.parentObject(self.planeBlend, self.noMoveGroup)
		self.parentObject(self.wireDeformerCurve, self.noMoveGroup)
		self.parentObject("%sBaseWire" % str(self.wireDeformerCurve), self.noMoveGroup)
		self.parentObject(self.moveGroup, self.masterControlCurve)
		masterControlGroup = cmds.group(self.masterControlCurve, name = "%s_MST_CTRL_GRP" % self.name, parent = self.masterGroup)
		
		# Hide objects.
		self.hideObject(self.planeBlend)
		self.hideObject(self.wireDeformerCurve)
		self.hideObject("%sBaseWire" % str(self.wireDeformerCurve))
		
		# Constrain the plane to the locators. Then delete the constraint and the locators.
		constraint = cmds.pointConstraint(self.locators[0], self.locators[1], masterControlGroup)
		cmds.delete(constraint)
		for locator in self.locators:
			cmds.delete(locator)
	
	# Creates a top and bottom locators, which should be placed at the top and bottom of the prospective ribbon spine.
	def createLocators(self):
		locator1 = cmds.spaceLocator (name = "bottomSpine_LOC")
		locator2 = cmds.spaceLocator (name = "topSpine_LOC" )
		cmds.move (0, 5, 0, locator1)
		cmds.move (0, 10, 0, locator2)
		self.locators = [locator1, locator2]
	
	# Creates a NURBS plane equal in length to the distance between the two locators.
	def createPlane(self):
		# First we find the distance between the two locators.
		t1 = cmds.getAttr ("%s.translate" % self.locators[0][0])
		t2 = cmds.getAttr ("%s.translate" % self.locators[1][0])
		distMeasure = cmds.distanceDimension (sp = (t1[0][0], t1[0][1], t1[0][2]), ep = (t2[0][0], t2[0][1], t2[0][2]))
		self.distance = cmds.getAttr ("%s.distance" % distMeasure)
		cmds.delete (cmds.pickWalk (distMeasure, direction = "up"))
		# Then we create a plane, freeze its transforms, and delete its construction history.
		plane = cmds.nurbsPlane (name = self.name +"_GEO", width = self.distance, lengthRatio = (1.0 / self.joints), patchesU = self.joints, axis = (0, 0, 1))
		cmds.rotate(0, 0, 90, plane[0])
		cmds.makeIdentity (plane[0], apply = True, translate = True, rotate = True, scale = True)
		cmds.delete (plane, constructionHistory = True)
		del plane[1]		
		return plane[0]
		
	# Duplicates the plane and shifts it.
	def createPlaneBlend(self):
		planeBlend = cmds.duplicate (self.plane, name = "%s_BLND" % self.name)
		cmds.move (self.blendOffset, 0, 0, planeBlend[0])
		return planeBlend[0]
	
	# Places a follicle in each span of the NURBS plane. Returns the follicles in a list.
	def createFollicles(self):
		follicles = []
		planeShape = cmds.listRelatives(self.plane)[0]
		# Finds the center of each NURBS span.
		interval = 1.0 / self.joints
		current_interval = 0
		spans = []
		# Loops through the intervals to distribute the follicles evenly.
		while current_interval <= 1.0:
			spans.append(current_interval)
			print str(current_interval) +" += "+ str(interval)
			current_interval += interval
			# Inaccurate floats would stop the loop prematurely, so added this condition to break it.
			if current_interval >= 1:
				spans.append(1.0)
				continue
		
		# Places the follicles and connects them to the NURBS plane.
		group = cmds.group (name = self.name +"_FOL_GRP", empty = True);
		for fol in range(self.joints):
			follicle = cmds.createNode("follicle", name = "%s_FOL_%s" % (self.name, str(fol)))
			follicleTransform = cmds.listRelatives(follicle, parent = True)
			cmds.connectAttr("%s.outRotate" % follicle, follicleTransform[0] +".rotate")
			cmds.connectAttr("%s.outTranslate" % follicle, follicleTransform[0] +".translate")
			cmds.connectAttr("%s.local" % planeShape, follicle +".inputSurface")
			cmds.connectAttr("%s.worldMatrix" % planeShape, follicle +".inputWorldMatrix")
			cmds.setAttr("%s.parameterU" % follicle, (spans[fol] + spans[fol + 1]) / 2)
			cmds.setAttr("%s.parameterV" % follicle, 0.5)
			cmds.parent(follicleTransform, group, relative=True)
			follicles.append(follicle)
		self.hideObject(group)
		self.parentObject(group, self.noMoveGroup)
		return follicles
		
	# Creates bind joints and constrains and parents them to each follicle.
	def createJoints(self):
		joints = []
		group = cmds.group(name = "%sBIND_JNT_GRP" % self.name, empty = True)
		for follicle in self.follicles:
			cmds.select (clear = True)
			follicleTransform = cmds.listRelatives(follicle, parent = True)
			joint = cmds.joint (name = "%s_BIND_JNT_%s" % (self.name, str(self.follicles.index(follicle))))
			constraint = cmds.parentConstraint (follicleTransform, joint, weight = 1)
			joints.append(joint)			
		for jnt in joints:
			self.parentObject(jnt, group)
		self.parentObject(group, self.noMoveGroup)
		return joints
			
	# Creates control curves for the rig. Returns them in a list.
	def createControlCurves(self):
		topControlCurve = self.createControlCurve("%s_TOP_CTRL" % self.name)
		midControlCurve = self.createControlCurve("%s_MID_CTRL" % self.name)
		bottomControlCurve = self.createControlCurve("%s_BOTTOM_CTRL" % self.name)
		self.masterControlCurve = self.createControlCurve("%s_MASTER_CTRL" % self.name)
		
		# Place the controls in the appropriate location on the rig. Freeze transforms and delete history.
		cmds.move (0, self.distance / 2, 0, topControlCurve) 
		cmds.move (0, (self.distance / 2 ) * - 1, 0, bottomControlCurve)
		cmds.scale (1.25, 1.25, 1.25, self.masterControlCurve)
		curves = [topControlCurve, midControlCurve, bottomControlCurve, self.masterControlCurve]
		controlGroup = cmds.group(empty = True, name = "%s_CTRL_GRP" % self.name)
		for curve in curves:
			cmds.makeIdentity (curve, apply = True, translate = True, rotate = True, scale = True)
			cmds.delete (curve, constructionHistory = True)
			if curve != self.masterControlCurve:
				self.parentObject(curve, controlGroup)
				
		# Put the mid control into a separate group and constrain it between the two end controls.
		# Put the control group under the move group.
		midControlGroup = cmds.group(midControlCurve, name = "%s_MID_CTRL_GRP" % self.name, parent = controlGroup)
		cmds.pointConstraint (topControlCurve, bottomControlCurve, midControlGroup)
		self.parentObject(controlGroup, self.moveGroup)
		return curves
		
	# Returns square control curves with the specified name.
	def createControlCurve(self, name):
		span = (self.distance * (1.0 / self.joints)) * 0.5
		curve = cmds.curve(degree = 1, point = [(span, 0, span), (span * -1,0, span), (span * -1, 0, span * -1), (span, 0, span * -1), (span, 0, span)], name = name)
		cmds.setAttr("%s.overrideEnabled" % curve, 1)
		cmds.setAttr("%s.overrideColor" % curve, 17)
		return curve
	
	# Applies cluster deformers to the wire deformer curve. Links their translates to their respective control curve.
	def createClusterDeformers(self):
		# Create clusters on the top, middle, and bottom of our wire deformer curve.
		topCluster = cmds.cluster("%s.cv[1:2]" % self.wireDeformerCurve, name = "%s_TOP_CLS" % self.name, relative = True)
		midCluster = cmds.cluster("%s.cv[1]" % self.wireDeformerCurve, name = "%s_MID_CLS" % self.name, relative = True)
		bottomCluster = cmds.cluster("%s.cv[0:1]" % self.wireDeformerCurve, name = "%s_BOT_CLS" % self.name, relative = True)
		clusters = [topCluster, midCluster, bottomCluster]
		
		# Shift the pivots to the controls on the base plane.
		cmds.setAttr("%sShape.originY" % str(topCluster[1]), (self.distance / 2) * -1)
		cmds.setAttr("%sShape.originY" % str(bottomCluster[1]), (self.distance / 2))
		cmds.move( 0, (self.distance / 2) * -1, 0, "%s.rotatePivot" % str(topCluster[1]), "%s.scalePivot" % str(topCluster[1]))
		cmds.move(0, 0, 0, "%s.rotatePivot" % str(midCluster[1]),  "%s.scalePivot" % str(midCluster[1])) 
		cmds.move(self.distance / 2, 0, 0, "%s.rotatePivot" % str(bottomCluster[1]), "%s.scalePivot" % str(bottomCluster[1]))
		
		# Adjust the weight towards the end points.
		cmds.percent (topCluster[0], "%s.cv[1]" % self.wireDeformerCurve, value = 0.5)
		cmds.percent (bottomCluster[0], "%s.cv[1]" % self.wireDeformerCurve, value = 0.5)
		
		# Group the clusters and connect them to their respective controls.
		group = cmds.group (name = "%s_CLS_GRP" % self.name, empty = True)
		for index in range(len(clusters)):
			cmds.connectAttr("%s.translate" % str(self.controlCurves[index]), "%s.translate" % str(clusters[index][1]))
			self.parentObject(clusters[index][1], group)
		self.parentObject(group, self.noMoveGroup)
		self.hideObject(group)
		return clusters
	
	# Applies a nonlinear twist deformer to the blend shape and links it to the X rotation of the top and bottom controls.
	def createTwistDeformer(self):
		twistDeformer = cmds.nonLinear(self.planeBlend, type = "twist", name = "%s_TWIST_DFM" % self.name)
		cmds.rotate (0, -90, 180, twistDeformer)
		cmds.connectAttr("%s.rotateY" % str(self.controlCurves[0]), "%s.startAngle" % str(twistDeformer[0]))
		cmds.connectAttr("%s.rotateY" % str(self.controlCurves[2]),  "%s.endAngle" % str(twistDeformer[0]))
		cmds.setAttr("%s.rotateOrder" % str(self.controlCurves[2]), 3)
		cmds.setAttr("%s.rotateOrder" % str(self.controlCurves[0]), 3)
		self.parentObject(twistDeformer[1], self.noMoveGroup)
		self.hideObject(twistDeformer[1])
		return twistDeformer
		
	# Allows the rig to squash and stretch.
	def createStretchDeformer(self):
		# Get the length of the wire deformer curve to see if the rig is being stretched or squashed.
		arcLength = cmds.arclen (self.wireDeformerCurve, constructionHistory = True)
		length = cmds.getAttr("%s.arcLength" % arcLength)
		
		# Add attributes on the master control to enable squashing and stretching.
		cmds.addAttr(self.masterControlCurve, longName = "enable", attributeType = 'bool', keyable = True, hidden = False)
		cmds.addAttr(self.masterControlCurve, longName = "volume", attributeType = 'float', defaultValue = 1.0, keyable = True, hidden = False)
		
		# If the rig is being pulled or pushed, calculate the percentage.
		stretchDivideNode = cmds.createNode("multiplyDivide", name = "%s_STRETCH_DIV" % self.name)
		cmds.setAttr("%s.operation" % str(stretchDivideNode), 2)
		cmds.setAttr("%s.input2X" % str(stretchDivideNode), length)
		cmds.connectAttr("%s.arcLength" % arcLength, "%s.input1X" % str(stretchDivideNode))
		
		volumeDivideNode = cmds.createNode("multiplyDivide", name = "%s_VOL_DIV" % self.name)
		cmds.setAttr("%s.operation" % str(volumeDivideNode), 2)
		cmds.setAttr("%s.input1X" % str(volumeDivideNode), 1)
		cmds.connectAttr("%s.outputX" % str(stretchDivideNode), "%s.input2X" % str(volumeDivideNode))
		
		# Check to ensure that scaling is on.
		stretchConditionNode = cmds.createNode("condition", name = "%s_STRETCH_COND" % self.name)
		cmds.connectAttr("%s.enable" % str(self.masterControlCurve),  "%s.firstTerm" % str(stretchConditionNode))
		cmds.connectAttr("%s.outputX" % str(volumeDivideNode), "%s.colorIfTrue.colorIfTrueR" % str(stretchConditionNode))
		cmds.setAttr("%s.secondTerm" % str(stretchConditionNode), 1)
		
		# If so, scale the joints in Y and Z.
		for joint in self.bindJoints:
			cmds.connectAttr("%s.outColorR" % str(stretchConditionNode), "%s.scaleY" % joint)
			cmds.connectAttr("%s.outColorR" % str(stretchConditionNode), "%s.scaleZ" % joint)
	
	# Simple helper function to parent one object to another.
	def parentObject(self, object, group):
		cmds.parent (object, group, relative = True)
		
	# Simple helper function to hide visibility.
	def hideObject(self, object):
		cmds.setAttr("%s.visibility" % str(object), 0)