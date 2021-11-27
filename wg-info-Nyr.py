#!/usr/bin/python3

import os
import sys
import re
import subprocess
import threading

if 'html' in sys.argv:
	output = 'html'
	redfmt = '<span style="color: red;">'
	redbldfmt = '<span style="color: red; font-weight: bold;">'
	greenfmt = '<span style="color: green;">'
	greenbldfmt = '<span style="color: green; font-weight: bold;">'
	yellowfmt = '<span style="color: orange;">'
	yellowbldfmt = '<span style="color: orange; font-weight: bold;">'
	bldfmt = '<span style="font-weight: bold;">'
	endfmt = '</span>'
elif sys.stdout.isatty() or 'tty' in sys.argv:
	output = 'tty'
	redfmt = '\033[0;31m'
	redbldfmt = '\033[1;31m'
	greenfmt = '\033[0;32m'
	greenbldfmt = '\033[1;32m'
	yellowfmt = '\033[0;33m'
	yellowbldfmt = '\033[1;33m'
	bldfmt = '\033[1m'
	endfmt = '\033[0m'
else:
	output = 'pipe'
	redfmt = ''
	redbldfmt = ''
	greenfmt = ''
	greenbldfmt = ''
	yellowfmt = ''
	yellowbldfmt = ''
	bldfmt = ''
	endfmt = ''

peers = {}


def read_config(interface):
	peer_section = False

	peer_name = "*nameless*"
	peer_pubkey = ""
	peer_ip = ""
	c = 0

	with open('/etc/wireguard/%s.conf' % interface) as cfg:
		cfg_lines = cfg.readlines()
		for line in cfg_lines:
			c += 1
			line = line.strip()
			if line == "[Peer]":
				peer_name = cfg_lines[c-2]
				peer_name = peer_name[13:]
				peer_pubkey = cfg_lines[c].split('=', 1)[-1].strip()
				peer_ip = cfg_lines[c+2].split('=', 1)[-1].strip().split(',')[0].split('/')[0]
				peers[peer_pubkey] = {
					'name': peer_name,
					'ip': peer_ip,
				}

def show_info(interface):
	peer_section = False
	for line in subprocess.check_output(['wg', 'show', interface]).decode('utf-8').split("\n")[:-1]:
		line = line.strip()
		if line.startswith('peer:'):
			peer_section = True
			peer_pubkey = line.split(':', 1)[1].strip()
			if peers[peer_pubkey].get('online', True):
				colorfmt = greenfmt
				colorbldfmt = greenbldfmt
			else:
				colorfmt = redfmt
				colorbldfmt = redbldfmt
			print('  '+colorbldfmt+'peer'+endfmt+': '+colorfmt+peers[peer_pubkey]['name']+' ('+peer_pubkey+')'+endfmt)
		elif line.startswith('interface:'):
			peer_section = False
			interface = line.split(':', 1)[1].strip()
			print(yellowbldfmt+'interface'+endfmt+': '+yellowfmt+interface+endfmt)
		elif line.startswith('preshared key:') or line.startswith('private key:'):
			continue
		elif line:
			key = line.split(':')[0].strip()
			value = line.split(':', 1)[1].strip()
			indent = '    ' if peer_section else '  '
			print(indent+bldfmt+key+endfmt+': '+value)
		else:
			print(line)

def ping(pubkey):
	FNULL = open(os.devnull, 'w')
	retcode = subprocess.call(['ping', '-c1', '-W1', peers[pubkey]['ip']], stdout=FNULL, stderr=subprocess.STDOUT)
	peers[pubkey]['online'] = (retcode == 0)

def lookahead(iterable):
	"""Pass through all values from the given iterable, augmented by the
	information if there are more values to come after the current one
	(True), or if it is the last value (False).
	"""
	# Get an iterator and pull the first value.
	it = iter(iterable)
	last = next(it)
	# Run the iterator to exhaustion (starting from the second value).
	for val in it:
		# Report the *previous* value (more to come).
		yield last, True
		last = val
	# Report the last value.
	yield last, False


interfaces = [i.replace('.conf', '') for i in os.listdir('/etc/wireguard/') if i.endswith('.conf')]
for interface in interfaces:
	read_config(interface)


# Ping all peers in parallel so that this will just take 1 second in total
if 'ping' in sys.argv:
	threads = []
	for peer in peers:
		th = threading.Thread(target=ping, args=(peer,), daemon=True)
		threads.append(th)
		th.start()
	for th in threads:
		th.join()

if output == 'html':
	print('<html><head><title>Wireguard Statistics</title><meta http-equiv="refresh" content="120" /></head><body>')
	print('<pre>')
for interface, has_more in lookahead(interfaces):
	show_info(interface)
	if has_more:
		print("\n")
if output == 'html':
	print('</pre></body></html>')
