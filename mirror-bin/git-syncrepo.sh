#!/bin/sh -e
if [ "x$1" = "x" ] ; then
    echo "Path to sync expected."
    exit 1
fi
cd "$1"
exec git remote update
