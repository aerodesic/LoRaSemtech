#!/bin/bash
PORT=/dev/ttyUSB0
if [ "$1" = "-c" ]; then
  echo Removing all files from device
  ampy -p /dev/ttyUSB0 rmdir / >/dev/null 2>&1
  shift
fi

if [ -z "$1" ]; then
  MANIFEST="manifest.txt"
else
  MANIFEST="$1"
fi

for f in `cat $MANIFEST`; do
  # See if target directories exist
  if ! ampy -p $PORT put $f $f >/dev/null 2>&1; then
    # An error, so create sub directories as needed
    DIRS=`dirname $f | tr '/' ' '`
    dir=''
    if [ "$DIRS" != "." ]; then
      for d in $DIRS; do
        if [ -z "$dir" ]; then
          dir=$d
        else
          dir=$dir/$d
        fi
        if ! ampy -p $PORT ls $dir >/dev/null 2>&1; then
          echo Creating $dir
          ampy -p $PORT mkdir $dir >/dev/null 2>&1
        fi
      done
    fi
    # Do it again (report any errors)
    ampy -p $PORT put $f $f
  fi
  echo Downloaded $f
done
