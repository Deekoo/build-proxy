#!/bin/sh

# Flush the output table; note that this will be bad if anything else is
# sharing the server.
iptables -t nat -F OUTPUT

# All DNS queries go to the local machine.  That way DNS will work later...
iptables -t nat -m owner -A OUTPUT --uid-owner sudomesh -p tcp --dport 53 -j DNAT --to-destination 127.0.0.1
iptables -t nat -m owner -A OUTPUT --uid-owner sudomesh -p udp --dport 53 -j DNAT --to-destination 127.0.0.1

# Redirect all attempts to access remote HTTP servers to localhost:8081.
iptables -t nat -m owner -A OUTPUT --uid-owner sudomesh -p tcp --dport 80 \! -d 127.0.0.1 -j DNAT --to-destination 127.0.0.1:8081
# Redirect all attempts to access remote HTTPS servers to localhost:443.
iptables -t nat -m owner -A OUTPUT --uid-owner sudomesh -p tcp --dport 443 \! -d 127.0.0.1 -j DNAT --to-destination 127.0.0.1:443

# And reject everything else the build UID sends beyond localhost.
iptables -m owner -A OUTPUT --uid-owner sudomesh \! -d 127.0.0.1 -j REJECT
