#!/usr/bin/python
# This module contains API to facilitate the use of
# a relay host. The relay host is a privileged host
# that can run a specific service, to get access to
# that service other hosts must get to the relay host

import os
import sys
import socket
import getpass

def relay(strRelay, strRelayUser):
	"""This method checks if the current process has
	enough credential (ie running on strRelay as strRelayUser).
	If it is ok, the API returns.
	If not the API will re-execute the command on the relay host
	using ssh to connect to it"""
	try:
		relayHost = socket.gethostbyname(strRelay)
	except socket.gaierror:
		print "ERROR: Unable to relay cmd via %s as this hostname is not known." % strRelay
		print "The ldap config entry for the device in question may need to be updated."
		raise
	try:
		if strRelay != None:
			# Note: this will work for a host with multiple names but not multiple IPs
			if socket.gethostbyname(socket.gethostname()) != socket.gethostbyname(strRelay):
				# This script must be re-run on the relay host
				if strRelayUser != None:
					# And we take care of the user problem while we are at it
					print "Re-running the command on relay %s as %s, you may\n" \
						"be asked to type in your password:" % (strRelay, strRelayUser)
					os.system("ssh -t %s 'sudo -u %s %s --req_via_relay'" % (strRelay, \
						strRelayUser, " ".join(sys.argv)))
				else:
					print "Re-running the command on relay %s:" % (strRelay)
					os.system("ssh -t %s '%s --req_via_relay'" % (strRelay, " ".join(sys.argv)))
				return 1
		if strRelayUser != None:
			if getpass.getuser() != strRelayUser:
				# Must re-run as relayuser
				print "Re-running the command as %s, you may be asked to type in your password:" % (strRelayUser)
				os.system("sudo -u %s %s --req_via_relay" % (strRelayUser, " ".join(sys.argv)))
				return 1
		return 0
	except:
		raise
