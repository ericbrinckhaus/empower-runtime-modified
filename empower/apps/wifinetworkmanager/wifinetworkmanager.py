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
        self.RSSI_min = -50 # TODO ver valores de RSSI razonables
        self.quantum_max = 15000
        self.quantum_increase = 0.1
        self.quantum_decrease = 0.1
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
        if len(list(resultRates.get_points())):
            slices = list(resultRates.get_points())[0]
            for slc in slices.keys():
                rate = slices[slc]
                query = 'select * from lvap_slice where slice=\'' + slc + '\' order by time desc limit 1;'
                resultSlices = self.query(query)
                if len(list(resultSlices.get_points())):
                    lvaps = list(resultSlices.get_points())[0]
                    if len(lvaps):
                        for lvap in lvaps.keys():
                            if lvap == 'time' or lvap == 'slice':
                                continue
                            # do algorithm
                            self.decide(rate, lvaps[lvap], slc)
                    else:
                        print("Slice {} doesnt have any lvap".format(slc))
                else:
                    print ("No Slice-Lvap data")    
        else:
            print("No Slice-Rate data")

    def decide(self, rate, lvap, slc):
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
                    tx_bps += counter.tx_bps
                tx_bps = tx_bps / len(counters)
                # Si esta por debajo del rate prometido entonces tengo que hacer algo
                if (tx_bps < rate):
                    self.changeNetwork(lvap, slc, rate)
                else:
                    print("Lvap {} is trying more bit rate than promised.".format(lvap))
            else:
                print("[OK] Lvap {} has success rate of {}.".format(lvap, success_rate))
        else:
            print("Lvap {} is idle.".format(lvap))

    def changeNetwork(self, sta, slc, rate):
        if (self.try_handover(sta, slc, rate)):
            print('Handover')
        elif (self.try_change_quantum(sta, slc, rate)):
            print('Quantum Change')
        else:
            print('No actions taken, network too busy')
    
    def try_handover(self, sta, slc, rate):
        posibles_handovers = []
        lvap = self.context.lvaps[EtherAddress(sta)]
        blocks = self.blocks().sort_by_rssi(lvap.addr)
        def filterBlocks(block):
            if block.ucqm[lvap.addr]['mov_rssi'] > self.RSSI_min:
                return True
            else:
                return False
        # Filtramos los wtp que tengan malo RSSI
        filtered_blocks = filter(filterBlocks, blocks)
        for block in filtered_blocks:
            query = 'select * from wifi_slice_stats where wtp=\'' + block.hwaddr() + '\' and slc=\'' + slc + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
            result = self.query(query)
            slice_stats = list(result.get_points())
            print("************* WIFI SLICE STATS SLC--> {} ; WTP-->: {}:::: {}".format(slc, block.hwaddr(), slice_stats))
            tx_bytes = 0
            for stats in slice_stats:
                tx_bytes += stats['tx_bytes']
            tx_bps = tx_bytes / (self.every/1000)
            # si el rate de la slice en el wtp es menor al rate prometido, es un candidato
            if tx_bps < rate:
                posibles_handovers.append({'block':block, 'rate':tx_bps})
        if len(posibles_handovers) > 0:
            def get_rate(blck):
                return blck['rate']
            # Ordeno los bloques por rate asi me quedo con el que tenga menos
            posibles_handovers.sort(get_rate)
            # Do Handover
            lvap.blocks = posibles_handovers[0]['block']
            return True
        else:
            return False

    def try_change_quantum(self, sta, slc, rate):
        lvap = self.context.lvaps[EtherAddress(sta)]
        wtp = lvap.wtp.addr
        actual_slice = self.context.wifi_slices[str(slc)]
        wtp_quantum = actual_slice.properties['quantum']
        if EtherAddress(wtp) not in actual_slice.properties['devices']:
            wtp_quantum = actual_slice.properties['devices'][wtp]['quantum']
        if wtp_quantum < self.quantum_max:
            # incrementar 10% del quantum en este wtp para esta slice
            updated_slice = {
                'slice_id': actual_slice.slice_id,
                'properties': {
                    'amsdu_aggregation': actual_slice.properties['amsdu_aggregation'],
                    'quantum': actual_slice.properties['quantum'] + 1,
                    'sta_scheduler': actual_slice.properties['sta_scheduler']
                },
                'devices': actual_slice.devices
            }
            addr = EtherAddress(wtp)
            if addr not in updated_slice['devices']:
                updated_slice['devices'][addr] = {
                    'amsdu_aggregation': actual_slice.properties['amsdu_aggregation'],
                    'quantum': actual_slice.properties['quantum'] + actual_slice.properties['quantum']*self.quantum_increase,
                    'sta_scheduler': actual_slice.properties['sta_scheduler']
                }
            else:
                updated_slice['devices'][addr]['quantum'] = updated_slice['devices'][addr]['quantum'] + updated_slice['devices'][addr]['quantum']*self.quantum_increase
            # Decrementar los quantum para las slices que estan pasadas del rate prometido en el WTP
            updated_slice2 = self.decreaseQuantum(slc, wtp, updated_slice)
            self.context.upsert_wifi_slice(**updated_slice2)
            return True
        else:
            return False

    def decreaseQuantum(self, slc, wtp, updated_slice):
        # para todas las slices en el wtp
        for idx in self.context.wifi_slices:
            if idx != slc:
                query = 'select * from wifi_slice_stats where wtp=\'' + wtp + '\' and slc=\'' + idx + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
                result = self.query(query)
                slice_stats = list(result.get_points())
                if len(slice_stats) > 0:
                    query = 'select * from slices_rates order by time desc limit 1;'
                    resultRates = self.query(query)
                    if len(list(resultRates.get_points())):
                        slices = list(resultRates.get_points())[0]
                        if idx in slices:
                            rate = slices[idx]
                            tx_bytes = 0
                            for stats in slice_stats:
                                tx_bytes += stats['tx_bytes']
                            tx_bps = tx_bytes / (self.every/1000)
                            # si el rate de la slice en el wtp es menor al rate prometido, es un candidato
                            if tx_bps > rate:
                                addr = EtherAddress(wtp)
                                if addr not in updated_slice['devices']:
                                    updated_slice['devices'][addr] = {
                                        'amsdu_aggregation': updated_slice.properties['amsdu_aggregation'],
                                        'quantum': updated_slice.properties['quantum'] - updated_slice.properties['quantum']*self.quantum_decrease,
                                        'sta_scheduler': updated_slice.properties['sta_scheduler']
                                    }
                                else:
                                    updated_slice['devices'][addr]['quantum'] = updated_slice['devices'][addr]['quantum'] - updated_slice['devices'][addr]['quantum']*self.quantum_decrease

        return updated_slice

    def changeNetwork2(self, sta, slc, rate):
        # por ahora muevo al wtp con rssi mas cercano --- despues cambiar esto
        #print('*************** SELF BLOCKS: ', self.blocks())
        #lvap = self.context.lvaps[EtherAddress(sta)]
        #print('*************** BLOCKS ORDENADOS POR RSSI: {}; **** LVAP ADDR ***: {}; **** LVAP ****: {};'.format(self.blocks().sort_by_rssi(lvap.addr), lvap.addr, lvap))
        #print('*************** BLOQUE DEL LVAP: ', lvap.blocks)
        #lvap.blocks = self.blocks().sort_by_rssi(lvap.addr).first()
        #lvap.blocks = self.blocks()[randrange(4)]
        print('**************** SLICES: ', self.context.wifi_slices)
        asd = self.context.wifi_slices['0']
        print('************* SLICE: ', asd)
        asd2 = {
            'slice_id': asd.slice_id,
            'properties': {
                'amsdu_aggregation': asd.properties['amsdu_aggregation'],
                'quantum': asd.properties['quantum'] + 1,
                'sta_scheduler': asd.properties['sta_scheduler']
            },
            'devices': asd.devices
        }
        addr = EtherAddress('64:66:B3:8A:52:62')
        if addr not in asd2['devices']:
            asd2['devices'][addr] = {
                'amsdu_aggregation': asd.properties['amsdu_aggregation'],
                'quantum': asd.properties['quantum'] + 1000,
                'sta_scheduler': asd.properties['sta_scheduler']
            }
        else:
            asd2['devices'][addr]['quantum'] = asd2['devices'][addr]['quantum'] + 1000
        print('************ ASD2: ', asd2)
        self.context.upsert_wifi_slice(**asd2)


    # iperf usa Mbits para medir el rate
    def to_Mbits(self, byte):
        return byte * 8 / 1000000

def launch(context, service_id, every=EVERY):
    """ Initialize the module. """

    return NetworkManager(context=context, service_id=service_id, every=every)
