#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import telnetlib, socket

import os
import subprocess

from random import randint

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.


################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", False)
		self.keepAlive = pluginPrefs.get("keepAlive", False)

		self.myLink = None
		self.myLinkAuth = ""
		
		self.myLinkIP = ""

	########################################

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		# Since the dialog closed we want to set the debug flag - if you don't directly use
		# a plugin's properties (and for debugLog we don't) you'll want to translate it to
		# the appropriate stuff here.
		if not userCancelled:
			self.debug = valuesDict.get("showDebugInfo", False)
			self.keepAlive = valuesDict.get("keepAlive", False)
			if self.debug:
				indigo.server.log("Debug logging enabled")
			else:
				indigo.server.log("Debug logging disabled")
			if self.keepAlive:
				indigo.server.log("Keepalive enabled")
			else:
				indigo.server.log("Keepalive disabled")

	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
		#self.debugLog(str(valuesDict))
		#self.debugLog(str(typeId))
		#self.debugLog(str(devId))
		if not userCancelled:
			if (str(typeId) == "mylink"):
				#self.debugLog("myLink")
				dev = indigo.devices[devId]
				devIP = valuesDict["devIP"]
				self.myLinkIP = devIP
				dev.stateListOrDisplayStateIdChanged()
				dev.updateStateOnServer("devIP",devIP)
			if (str(typeId) == "motor"):
				#self.debugLog("Motor")
				dev = indigo.devices[devId]
				targetAddr = valuesDict["devAddr"]
				targetCh = valuesDict["devCh"]
				if (str(targetCh) == ""):
					targetCh = "*"
				targetID = str(targetAddr) + "." + str(targetCh)
				dev.stateListOrDisplayStateIdChanged()
				dev.updateStateOnServer("devAddrCh",targetID)
		return True

	def deviceStartComm(self, dev):
		#dev.stateListOrDisplayStateIdChanged()
		if (dev.deviceTypeId == "mylink"):
			devIP = dev.ownerProps['devIP']
			devPort = dev.ownerProps['devPort']
			devAuth = dev.ownerProps['devAuth']
			connTimeout = dev.ownerProps['connTimeout']
			
			indigo.server.log("Connecting to MyLink:  %s" % str(devIP))
			try:
				self.myLink = telnetlib.Telnet(devIP, int(devPort), timeout = int(connTimeout))
				self.myLinkAuth = str(devAuth)
				self.myLinkIP = devIP
				self.debugLog(str(self.myLink))
			except socket.timeout as t:
				self.errorLog("Error connecting to MyLink on %s: Connection timed out" % devIP)


	def deviceStopComm(self, dev):
		if (dev.deviceTypeId == "mylink"):
			try:
				self.myLink.close()
			except:
				pass
			finally:
				self.myLink = None
				self.myLinkAuth = ""
				self.myLinkIP = ""

	def myLinkCmdSingle(self, pluginAction):
		self.debugLog("myLinkCmdSingle action called:")
		#self.debugLog(str(pluginAction))
		targetDev = pluginAction.deviceId
		targetAddr = indigo.devices[int(targetDev)].ownerProps["devAddr"]
		targetCh = indigo.devices[int(targetDev)].ownerProps["devCh"]
		if (targetCh == ""):
			targetCh = "*"
		targetID = str(targetAddr) + "." + str(targetCh)
		
		method = str(pluginAction.pluginTypeId)
		method = method.replace(".1","").replace(".2","")
	
		message_id = randint(0, 1000)
	
		self.debugLog("Target device: " + str(targetID))

		payload = '{ "id":%s, "method": "%s", "params": { "auth": "%s", "targetID" : "%s"} }' % (message_id,method,self.myLinkAuth,targetID)
		
		indigo.server.log("Sending payload:  %s" % str(payload))

		self.myLink.write(payload)
		
		reply = ""
		
		reply = self.myLink.read_very_eager()
		self.debugLog("Reply from %s: %s" % (message_id,str(reply)))

		
	def myLinkRead(self, pluginAction):
		self.debugLog("myLinkRead action called:")
		reply = ""
		
		reply = self.myLink.read_very_eager()
		self.debugLog("Reply: " + str(reply))

	def check_ping(self):
		p = subprocess.Popen("/sbin/ping -c1 "+self.myLinkIP,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		p.communicate()

		if p.returncode == 0:
			pingstatus = "Network Active"
			self.debugLog(pingstatus)
		else:
			pingstatus = "MyLink Network error"
			self.errorLog(pingstatus)
		
	def runConcurrentThread(self):
		try:
			while True:
				if self.keepAlive:
					if (self.myLinkIP <> ""):
						self.check_ping()
					else:
						self.debugLog("Couldn't ping MyLink as no MyLink device found.")
				self.sleep(20) # in seconds
		except self.StopThread:
			# do any cleanup here
			pass