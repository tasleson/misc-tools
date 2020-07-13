#!/bin/ksh

# Update IP address for zone edit ddns
#
# How did I get here?
# Using ddclient on openbsd 6.7 is failing with:
# "SSLeay.c: loadable library and perl binaries are mismatched (got handshake key 0xb700000, needed 0xb600000)"
#
# So rolling my own script.
#
# Using ksh for OpenBSD because bash is failing to install for 6.7 :-/

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

# Storing the user configurable stuff in a sep. file
# eg. ETHERNET, USERNAME, PASSWORD, HOSTS
. $SCRIPTPATH/ddns.conf

STATE=/root/ddns
LOGFILE=/var/log/ddns.log
LAST_IP=$STATE/ip
LAST_UPDATE=$STATE/update

FORCE_UPDATE_DURATION="2073600" # Every 24 days

# Which ethernet interface to obtain IP from
ETH=$ETHERNET

# username and password
UN=$USERNAME
PW=$PASSWORD

# Put 1 or more hosts to be assosiated with IP seperated with ,
HOSTS=$HOSTS

# Current time epoch
NOW=$(date +'%s') || exit 1

l() {
    echo "$(date) $1" >> $LOGFILE
}

update_ip() {
    typeset ip=$1

    ret=$(curl -s -u $UN:$PW "https://dynamic.zoneedit.com/auth/dynamic.html?host=$HOSTS&dnsto=$ip") || exit 1
    l "Changing IP from $oldip to $curip"
    l "    $ret"

    if [[ "$ret" ==  \<SUCCESS* ]] ; then
        # push succeeded - cache the new ip
        echo $ip > $LAST_IP || exit 1
        echo "$NOW" > $LAST_UPDATE || exit 1
        exit 0
    else
	l "Failed to update IP $ret"
        exit 1
    fi
}

mkdir -p $STATE || exit 1

# force files to exist
touch $LAST_IP || exit 1
touch $LAST_UPDATE || exit 1

# get last known IP
oldip=$(cat $LAST_IP) || exit 1

# get current IP
curip=$(ifconfig $ETH | awk '$1 == "inet" {print $2}') || exit 1

# Option B
# curip=$(curl -s v4.ident.me) || exit 1

# Check if IP address is valid by pinging it
ping -c 1 -w 2 -q $curip > /dev/null 2>&1
if [ $? -ne 0 ] ; then
    l "IP not pingable $curip"
    exit 1
fi

lastupdate=$(cat $LAST_UPDATE) || exit 1

# Check for empty last update
if [ -z "$lastupdate" ] ; then
    lastupdate="0"
fi

if [ "$oldip" = "$curip" ] ; then
    l "IP did not change $oldip"
    elapsed=$(($NOW - $lastupdate))

    if [ $elapsed -ge $FORCE_UPDATE_DURATION ] ; then
        l "Forcing update as $elapsed seconds have elapsed since last update"
        update_ip $curip
    fi
    exit 0
else
    update_ip $curip
fi
exit 0
