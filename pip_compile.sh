#!/bin/bash
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

for file in requirements*.in ; do
    pip-compile -rU --no-header $file
    out=`echo $file | sed "s/.in/.txt/"`
    header=`head -3 tox.ini`
    { cat tox.ini | head -n 2 ; cat $out; } >  $out.new
    mv $out.new $out
done