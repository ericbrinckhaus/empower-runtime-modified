#!/bin/sh
iperf3 -c localhost -t 10 -u
echo "despues de iperf"
sleep 10
echo "despues de sleep"