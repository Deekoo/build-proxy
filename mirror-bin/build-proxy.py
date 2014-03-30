#!/usr/bin/env python

"""
To use:
Step 0: Configure your archive URL correctly.
"""
ARCHIVE = "http://localhost/~sudomirror/mirror/http/"
"""
The docs will assume that the firmware is built by user sudomesh and
the mirror is owned by user sudomirror.

redirect all network access from the build account to localhost.
    (See firewall.sh for an example.)

Put the git and svn rearrangers in ~sudomesh/bin/ and make sure that
~sudomesh/bin/ is at the beginning of sudomesh's path.  You may need to log
out and back in, or rehash.

Start (as the mirror user) build-proxy.py.

"""

import sys
import select
import socket

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
sock.bind(("127.0.0.1",8081))
sock.listen(2)

def read_line(sock):
    ret = ''
    while 1:
        c = sock.recv(1)
        ret += c
        if c=='\n':
            return ret
        elif not c:
            return ret

def handle_req(sock):
    while 1:
        line = read_line(sock)
        if line.endswith("\012"):
            line = line[:-1]
        if line.endswith("\015"):
            line = line[:-1]
        if line.startswith("GET ") and line.endswith(" HTTP/1.1"):
            URL = line[4:-9]
            print "URL:",URL
        elif line.startswith("Host: "):
            HOST = line[6:]
            print "Host:",HOST
        elif not line:
            sock.send("HTTP/1.1 301 Moved Permanently\015\012Location: "+ARCHIVE+HOST+URL+"\015\012\015\012")
            sock.shutdown(1)
            sock.close()
            return
        else:
            pass
            #print "Ignoring HTTP header",line

peer = sock.accept()
while peer:
    print "Connected",peer[1]
    URL = 'nil'
    HOST = 'nil'
    handle_req(peer[0])
    peer = sock.accept()
