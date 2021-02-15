"""
    Version: 1.1
    Author: Kirth Gersen
    Date created: 6/5/2016
    Date modified: 9/12/2016
    Python Version: 2.7
"""

from __future__ import print_function
import json
import sys
import csv

db = {}

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def main():
    global minStart
    """main program"""

    csv.register_dialect('iperf3log', delimiter=',', quoting=csv.QUOTE_MINIMAL)
    csvwriter = csv.writer(sys.stdout, 'iperf3log')

    if len(sys.argv) == 2:
        if (sys.argv[1] != "-h"):
            sys.exit("unknown option")
        else:
            csvwriter.writerow(["date", "ip", "localport", "remoteport", "duration", "protocol", "num_streams", "cookie", "sent", "sent_mbps", "rcvd", "rcvd_mbps", "totalsent", "totalreceived"])
            sys.exit(0)

    # accummulate volume per ip in a dict
    minStart = 0
    
    # highly specific json parser
    # assumes top { } pair are in single line

    jsonstr = ""
    i = 0
    m = False
    for line in sys.stdin:
        i += 1
        if line == "{\n":
            jsonstr = "{"
            #print("found open line %d",i)
            m = True
        elif line == "}\n":
            jsonstr += "}"
            #print("found close line %d",i)
            if m:
                process(jsonstr,csvwriter)
            m = False
            jsonstr = ""
        else:
            if m:
                jsonstr += line
            #else:
                #print("bogus at line %d = %s",i,line)

def process(js,csvwriter):
    global minStart
    #print(js)
    try:
        obj = json.loads(js)
    except:
        eprint("bad json")
        pass
        return False 
    try:
        # caveat: assumes multiple streams are all from same IP so we take the 1st one
        # todo: handle errors and missing elements

        ts = obj["start"]["timestamp"]["time"].replace(',', '.')
        timesecs = obj["start"]["timestamp"]["timesecs"]

        for interval in obj["intervals"]:

            start2 = interval["sum"]["start"]
            if minStart == 0:
                minStart = timesecs
            start2 = start2 + timesecs - minStart
            start = interval["sum"]["start"]
            end = interval["sum"]["end"]
            z_bytes = interval["sum"]["bytes"]
            bps = interval["sum"]["bits_per_second"]
            packets = interval["sum"]["packets"]
            lost_packets = interval["sum"]["lost_packets"]
            lost_percent = interval["sum"]["lost_percent"]

            csvwriter.writerow([ts, start2, start, end, z_bytes, bps, packets, lost_packets, lost_percent])
        return True
    except:
       eprint("error or bogus test:", sys.exc_info()[0])
       pass
       return False

def dumpdb(database):
    """ dump db to text """
    for i in database:
        (s, r) = database[i]
        print("%s, %d , %d " % (i, s, r))

if __name__ == '__main__':
    main()