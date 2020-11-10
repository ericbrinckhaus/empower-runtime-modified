"""WiFi Nwtwork Manager Primitive."""

import time
import math

from datetime import datetime

from construct import Struct, Int8ub, Int16ub, Int32ub, Bytes, Array
from construct import Container

import empower.managers.ranmanager.lvapp as lvapp

from empower.core.ssid import WIFI_NWID_MAXSIZE
from empower.core.etheraddress import EtherAddress
from empower.managers.ranmanager.lvapp.wifiapp import EWiFiApp
from empower.core.app import EVERY

class NetworkManager(EWiFiApp):
    """WiFi Netork Manager Primitive.

    This manages de network with collected statistics.

    Parameters:
        every: the loop period in ms (optional, default 2000ms)

    Example:
        POST /api/v1/projects/52313ecb-9d00-4b7d-b873-b55d3d9ada26/apps
        {
            "name": "empower.apps.wifinetworkmanager.wifinetworkmanager",
            "params": {
                "every": 2000
            }
        }
    """

    def __init__(self, context, service_id, every=EVERY):

        super().__init__(context=context,
                         service_id=service_id,
                         every=every)

        # Data structures
        self.threshold = 0.75
        self.changes = {}

    def __eq__(self, other):
        if isinstance(other, NetworkManager):
            return self.every == other.every
        return False

    def to_dict(self):
        """Return JSON-serializable representation of the object."""

        out = super().to_dict()
        out['changes'] = self.changes

        return out

    def loop(self):
        """Check and update network """
        self.checkNetworkSlices()

    def checkNetworkSlices(self):
        query = 'select * from slices_rates order by time desc limit 1;'
        resultRates = self.query(query)
        query = 'select * from lvap_slice order by time desc limit 1;'
        resultSlices = self.query(query)
        if len(list(resultRates.get_points())):
            slices = list(resultRates.get_points())[0]
            for slc in slices.keys():
                rate = slices[slc]
                if len(list(resultSlices.get_points())):
                    datos_slices = list(resultSlices.get_points())[0]
                    lvaps = datos_slices[slc]
                    if len(lvaps):
                        for lvap in lvaps:
                            # do algorithm
                            self.decide(rate, lvap, slc)
                    else:
                        print("Slice {0} doesnt have any lvap", slc)
                else:
                    print ("No Slice-Lvap data")    
        else:
            print("No Slice-Rate data")

    def decide(self, rate, lvap, slc):
        lvap = '6C:C7:EC:98:16:65'
        # obtengo las stats de rate control desde la ultima vez que pregunte
        query = 'select * from lvap_rc_stats where sta=\'' + lvap + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
        result = self.query(query)
        rates_list = list(result.get_points())
        # sumo todos las last_attempts y last_successes
        total_last_attempts = 0
        total_last_successes = 0
        for rates in rates_list:
            # for rate in rates.keys():
            #     total_last_attempts += rates[rate]["last_attempts"]
            #     total_last_successes += rates[rate]["last_successes"]
            total_last_attempts += rates["last_attempts"]
            total_last_successes += rates["last_successes"]
        # calculo exitos sobre intentos totales
        if total_last_attempts > 0:
            success_rate = total_last_successes / total_last_attempts
            if success_rate < self.threshold:
                query = 'select * from lvap_counters_stats where sta=\'' + lvap + '\' order by time desc limit 3;'
                result = self.query(query)
                counters = list(result.get_points())
                tx_bps = 0
                for counter in counters:
                    tx_bps += counters[counter]
                tx_bps = tx_bps / len(counters)
                # Si esta por debajo del rate prometido entonces tengo que hacer algo
                if (tx_bps < rate):
                    self.changeNetwork(lvap, slc, rate)
                else:
                    print("Lvap {0} is trying more bit rate than promised.", lvap)
            else:
                print("[OK] Lvap {0} has success rate of {1}.", lvap, success_rate)
        else:
            print("Lvap {0} is idle.", lvap)

    def changeNetwork(self, sta, slc, rate):
        # por ahora muevo al wtp con rssi mas cercano --- despues cambiar esto
        lvap = self.context.lvaps[sta]
        lvap.blocks = self.blocks().sort_by_rssi(lvap.addr).first()

    # iperf usa Mbits para medir el rate
    def to_Mbits(self, byte):
        return byte * 8 / 1000000

def launch(context, service_id, every=EVERY):
    """ Initialize the module. """

    return NetworkManager(context=context, service_id=service_id, every=every)
