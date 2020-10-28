#!/usr/bin/python
# This module contains API to facilitate the control
# and use of terminal servers
# Currently only Digiport TS is supported but 
# it should be trivial to support other devices

import os
import os.path
import sys
import commands

SSH_KEYS_DIR = "/etc/sshkeys"

def create_termserverport_obj(ldapobjSerialPort):
	"""Create the correct TerminalServerPort compatible object
	depending on the configuration stored in an LDAP node
	given by ldapobjSerialPort of type ldapObject"""
	try:
		strType = ldapobjSerialPort.get_attr("type")[0]
		strServer = ldapobjSerialPort.get_parent().get_attr("cn")[0]
		dictConfig = ldapobjSerialPort.get_attr("config")
		if dictConfig != None:
			lstConfig = " ".join(dictConfig).split()
			dictTuppleConfig = dict([ (cfg.split("=")[0], cfg.split("=")[1]) for cfg in lstConfig ])
		else:
			dictTuppleConfig = {}

		# Hack to force telnet till all ldap config entries for digi's
		# can be changed from ssh to telnet.
		return TelnetTerminalServerPort( strServer, dictTuppleConfig )

		#if strType == "ssh":
		#	return SshTerminalServerPort(strServer, dictTuppleConfig)
		#else if strType == "telnet":
		#	return TelnetTerminalServerPort( strServer, dictTuppleConfig )
		#else:
		#	return TerminalServerPort()

	except:
		raise
	

class TerminalServerPort:
	def __init__(self):
		"""Constructor"""
	
	def connect(self):
		"""Connect to a serial port, this API returns only
		when the connection is terminated"""
		raise NotImplementedError, "connect not supported on this serial port"
	
	def disconnect(self):
		"""Terminate all active connections to this port"""
		raise NotImplementedError, "disconnect not supported on this serial port"
		
	def configure(self, dictConfig):
		"""Configure this port, this API may need to be run by a user
		with higher privileges. The dictConfig parameter should be a dictionary
		that contains:
		baudrate: baudrate of the serial port
		databits: number of data bits per frame
		parity: is there a parity bit, if so odd or even (no, odd, even)
		stopbits: number of stop bits
		fc: flow control (hard, soft, no)"""
		raise NotImplementedError, "configure not supported on this serial port"

class SshTerminalServerPort(TerminalServerPort):
	"""TerminalServer implementation for terminal servers that support
	access using SSH. 
	When creating a new instance, you must provide the terminal server network
	name and a dictionary that contains the following elements:
	port: port to use to connect.
	Optional parameters are:
	user: user to use to connect.
	key: set the key file to be used, if no path is given the script will look in SSH_KEYS_DIR
	"""
	def __init__(self, strServer, dictConfig):
		self.strServer = strServer
		if dictConfig == None:
			raise RuntimeError, "missing configuration for ssh terminal server port"
		self.dictConfig = dictConfig
	
	def ssh_exec(self, strCmd, strOptions = None):
		"""Helper method"""
		cmd = "ssh -t -e '^]' %s" % (self.strServer)
		if strOptions != None:
			cmd += " " + strOptions
		if self.dictConfig.has_key("user"):
			cmd += " -l %s" % (self.dictConfig["user"])
		if self.dictConfig.has_key("key"):
			if self.dictConfig["key"].count("/") != 0:
				cmd += " -i %s" % (self.dictConfig["key"])
			else:
				cmd += " -i %s/%s" % (SSH_KEYS_DIR, self.dictConfig["key"])
		cmd += " " + strCmd
		os.system(cmd)
	
	def connect(self):
		try:
			print "Connecting to serial port using SSH, to close connection use ^] then '.'"
			self.ssh_exec("", "-p %s" % (self.dictConfig["port"]))
			print "Connection to serial port terminated."
		except:
			raise RuntimeError, "(ssh) failed to connect to serial port on %s" % (self.strServer)
		
	def disconnect(self):
		print "Closing all open connection to serial port ...",
		try:
			cmd = "ps -eo pid,args | grep -v grep | grep ssh"
			cmd += " | grep %s" % (self.strServer)
			cmd += " | grep ' -p %s'" % (self.dictConfig["port"])
			if self.dictConfig.has_key("user"):
				cmd += " | grep ' -l %s'" % (self.dictConfig["user"])
			cmd += r" | sed -e 's/\([0-9]*\)[ ]*.*/\1/'"
			(iRet, strPID) = commands.getstatusoutput(cmd)
			if strPID.isspace() or (strPID == ""):
				print "done."
				return
			if (not strPID.isdigit()) or (iRet != 0):
				raise RuntimeError
			cmd = "kill %s" % (strPID)
			iRet = os.system(cmd)
			if iRet != 0:
				raise RuntimeError
			print "done."
		except:
			raise RuntimeError, "(ssh) failed to close connections to serial port on %s" % (self.strServer)
		
	def configure(self, dictConfig):
		raise NotImplementedError, "configure not supported on this serial port"

class TelnetTerminalServerPort(TerminalServerPort):
	"""TerminalServer implementation for terminal servers that support access using telnet. 
	When creating a new instance, you must provide the terminal server network
	name and a dictionary that contains the following elements:
	port: port to use to connect.
	Optional parameters are:
	user: user to use to connect.
	"""
	def __init__(self, strServer, dictConfig):
		self.strServer = strServer
		if dictConfig == None:
			raise RuntimeError, "missing configuration for telnet accessed terminal server port"
		self.dictConfig = dictConfig
	
	def telnet_exec(self, strPort = None, strOptions = None):
		"""Helper method"""
		cmd = "telnet -e '^]'"
		if strOptions != None:
			cmd += " " + strOptions
		if self.dictConfig.has_key("user"):
			cmd += " -l %s" % (self.dictConfig["user"])
		cmd += " " + self.strServer
		if strPort != None:
			cmd += " " + strPort
		iRet = os.system(cmd)
		if iRet != 0:
			raise RuntimeError

	def connect(self):
		try:
			print "Connecting to serial port using telnet ..."
			print "To close connection use ^], then 'quit' or ^D"
			self.telnet_exec( self.dictConfig["port"], None )
			print "Connection to serial port terminated."
		except:
			raise RuntimeError, "(telnet) failed to connect to serial port on %s" % (self.strServer)

	def disconnect(self):
#		print "Closing all open connection to serial port on %s ..." % ( socket.gethostname() )
		print "Closing all open connection to serial port ..."
		try:
			cmd = "ps -eo pid,args | grep -v grep | grep telnet"
			cmd += " | grep %s" % (self.strServer)
			cmd += " | grep ' %s'" % (self.dictConfig["port"])
			if self.dictConfig.has_key("user"):
				cmd += " | grep ' -l %s'" % (self.dictConfig["user"])
			cmd += r" | sed -e 's/\([0-9]*\)[ ]*.*/\1/'"
			(iRet, strPID) = commands.getstatusoutput(cmd)
			if strPID.isspace() or (strPID == ""):
				print "done."
				return
			if (not strPID.isdigit()) or (iRet != 0):
				raise RuntimeError
			cmd = "kill %s" % (strPID)
			iRet = os.system(cmd)
			if iRet != 0:
				raise RuntimeError
			print "done."
		except:
			raise RuntimeError, "(telnet) failed to close connections to serial port on %s" % (self.strServer)
		
	def configure(self, dictConfig):
		raise NotImplementedError, "configure not supported on this serial port"

