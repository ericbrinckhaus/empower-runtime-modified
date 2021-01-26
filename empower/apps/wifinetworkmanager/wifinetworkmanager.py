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
                "every": 6000
            }
        }
    """

    def __init__(self, context, service_id, every=EVERY*3):

        super().__init__(context=context,
                         service_id=service_id,
                         every=every)

        # Data structures
        self.threshold = 0.95 #TODO 0.75
        self.RSSI_min = 170 # TODO ver valores de RSSI razonables
        self.quantum_max = 15000 # Implica que q maximo va a ser 15000 + 10% = 16500
        self.quantum_min = 10000 # Implica que q minimo va a ser 10000 - 10% = 9000
        self.quantum_increase = 0.1
        self.quantum_decrease = 0.1
        self.changes = {}
        self.change_quantum = {}
        self.max_handovers = 1

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
        # initialize wtp handover counter
        self.wtp_handovers = {}
        for wtp in self.context.wtps.values():
            self.wtp_handovers[wtp.addr.to_str()] = 0

        # initialize actual quantum changes
        self.change_quantum = {}
        for slc in self.context.wifi_slices.keys():
            self.change_quantum[slc] = {}
            for wtp in self.context.wtps.values():
                self.change_quantum[slc][wtp.addr] = False

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
                            if lvap == 'time' or lvap == 'slice' or lvap == 'slice_id' or lvaps[lvap] == None:
                                continue
                            # do algorithm
                            self.decide(rate, lvaps[lvap], slc, slices)
                    else:
                        print("Slice {} doesnt have any lvap".format(slc))
                else:
                    print ("No Slice-Lvap data")    
        else:
            print("No Slice-Rate data")

    def decide(self, rate, lvap, slc, ratesProm):
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
        if total_last_attempts > 50: # si intento menos de 50 tomo como si estuviera idle porque es muy poco
            success_rate = total_last_successes / total_last_attempts
            if success_rate < self.threshold:
                query = 'select * from lvap_counters_stats where sta=\'' + lvap + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
                result = self.query(query)
                counters = list(result.get_points())
                tx_bps = 0
                for counter in counters:
                    tx_bps += counter["tx_bps"]
                tx_bps = tx_bps / len(counters)
                # Si esta por debajo del rate prometido entonces tengo que hacer algo
                if (tx_bps < rate):
                    self.changeNetwork(lvap, slc, rate, ratesProm)
                else:
                    self.write_log(slc, lvap, "N", "None", "LVAP + Rate than promised, rate: " + str(tx_bps))
                    print("Lvap {} is trying more bit rate than promised.".format(lvap))
            else:
                self.write_log(slc, lvap, "N", "None", "LVAP OK, success rate: " + str(success_rate))
                print("[OK] Lvap {} has success rate of {}.".format(lvap, success_rate))
        else:
            self.write_log(slc, lvap, "N", "None", "LVAP Idle")
            print("Lvap {} is idle.".format(lvap))

    def changeNetwork(self, sta, slc, rate, ratesProm):
        if (self.try_handover(sta, slc, rate, ratesProm)):
            print('Handover')
        elif (self.try_change_quantum(sta, slc, rate, ratesProm)):
            print('Quantum Change')
        else:
            self.write_log(slc, sta, "N", "None", "Network too busy")
            print('No actions taken, network too busy')
    
    def try_handover(self, sta, slc, rate, ratesProm):
        posibles_handovers = []
        lvap = self.context.lvaps[EtherAddress(sta)]
        blocks = self.blocks().sort_by_rssi(lvap.addr)
        def filterBlocks(block):
            if block.ucqm[lvap.addr]['mov_rssi'] > self.RSSI_min and block.hwaddr.to_str() != lvap.blocks[0].hwaddr.to_str():
                return True
            else:
                return False
        # Filtramos los wtp que tengan malo RSSI
        filtered_blocks = list(filter(filterBlocks, blocks))
        # obtengo el uso del wtp actual
        query = 'select * from wifi_channel_stats where wtp=\'' + lvap.blocks[0].hwaddr.to_str() + '\' and block_id=\'' + str(lvap.blocks[0].block_id) + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
        result = self.query(query)
        current_channel_stats = list(result.get_points())
        current_usage = 0
        for current_stats in current_channel_stats:
            current_usage += current_stats['tx'] # + current_stats['rx'] + current_stats['ed']
        # obtengo historial de handovers para verificar ping pong
        query = 'select * from lvaps_handover where sta=\'' + sta + '\' and time > now() - ' + str(int(self.every/1000)*10) + 's;'
        result = self.query(query)
        handover_list = list(result.get_points())
        for block in filtered_blocks:
            query = 'select * from wifi_channel_stats where wtp=\'' + block.hwaddr.to_str() + '\' and block_id=\'' + str(block.block_id) + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
            result = self.query(query)
            channel_stats = list(result.get_points())
            usage = 0
            for stats in channel_stats:
                usage += stats['tx'] #+ stats['rx'] + stats['ed']
            # si el uso del wtp es menor al actual, lo agrego como posible handover
            if usage < current_usage and self.wtp_handovers[block.hwaddr.to_str()] < self.max_handovers and not(self.ping_pong(handover_list, block.hwaddr.to_str())):
                posibles_handovers.append({'block':block, 'usage':usage})
        if len(posibles_handovers) > 0:
            # Ordeno los bloques por usage asi me quedo con el que tenga menos
            posibles_handovers.sort(key=lambda x: x['usage'])
            # escribo en logger
            self.write_log(slc, sta, "H", lvap.blocks[0].hwaddr.to_str() + "->" + posibles_handovers[0]['block'].hwaddr.to_str(), "Usage new WTP: " + str(posibles_handovers[0]['usage']))
            # Do Handover
            lvap.blocks = posibles_handovers[0]['block']
            self.wtp_handovers[posibles_handovers[0]['block'].hwaddr.to_str()] += 1
            # guardar cambios
            # generate data points
            points = []
            timestamp = datetime.utcnow()
            fields = {
                "wtp": posibles_handovers[0]['block'].hwaddr.to_str()
            }
            tags = {"sta": sta}
            sample = {
                "measurement": 'lvaps_handover',
                "tags": tags,
                "time": timestamp,
                "fields": fields
            }
            points.append(sample)
            # save to db
            self.write_points(points)
            return True
        else:
            # No encontre WTP con uso menor al actual, entonces me fijo si algun wtp tiene lvaps con rate mayor al prometido
            for block in filtered_blocks:
                extra_rate = 0
                for sta2 in self.context.lvaps:
                    lvap = self.context.lvaps[sta2]
                    if lvap.wtp.addr.to_str() == block.hwaddr.to_str():
                        lvap_slice = self.getSliceLvap(sta2)
                        promised_rate = ratesProm[lvap_slice]
                        lvap_rate = self.getLVAPRate(sta2)
                        if (lvap_rate - promised_rate) > 0:
                            extra_rate += (lvap_rate - promised_rate)
                if extra_rate > 0 and extra_rate >= rate and self.wtp_handovers[block.hwaddr.to_str()] < self.max_handovers and not(self.ping_pong(handover_list, block.hwaddr.to_str())):
                    posibles_handovers.append({'block':block, 'extra_rate':extra_rate})
            if len(posibles_handovers) > 0:
                # Ordeno los bloques por rate extra asi me quedo con el que tenga mas
                posibles_handovers.sort(key=lambda x: x['extra_rate'])
                # escribo en logger
                self.write_log(slc, sta, "H", lvap.blocks[0].hwaddr.to_str() + "->" + posibles_handovers[0]['block'].hwaddr.to_str(), "Extra rate new WTP: " + str(posibles_handovers[0]['extra_rate']))
                # Do Handover
                lvap.blocks = posibles_handovers[-1]['block']
                self.wtp_handovers[posibles_handovers[-1]['block'].hwaddr.to_str()] += 1
                # guardar cambios
                # generate data points
                points = []
                timestamp = datetime.utcnow()
                fields = {
                    "wtp": posibles_handovers[-1]['block'].hwaddr.to_str()
                }
                tags = {"sta": sta}
                sample = {
                    "measurement": 'lvaps_handover',
                    "tags": tags,
                    "time": timestamp,
                    "fields": fields
                }
                points.append(sample)
                # save to db
                self.write_points(points)
                return True
            else:
                return False

    def getSliceLvap(self, sta):
        query = 'select * from lvap_slice group by * order by time desc limit 1;'
        resultSlices = self.query(query)
        lvaps_slice = list(resultSlices.get_points())
        for lvap_slice in lvaps_slice:
            hasLvap = -1
            for key in lvap_slice.keys():
                if lvap_slice[key] == sta:
                    hasLvap = key
                    break
            if hasLvap != -1:
                return lvap_slice['slice_id']
        return ''

    def getLVAPRate(self, sta):
        query = 'select * from lvap_counters_stats where sta=\'' + sta.to_str() + '\' and time > now() - ' + str(int(self.every/1000)) + 's;'
        result = self.query(query)
        lvap_counter_stats = list(result.get_points())
        lvap_rate = 0
        for lvap_counter in lvap_counter_stats:
            lvap_rate += lvap_rate + lvap_counter["tx_bps"]
        lvap_rate = lvap_rate / len(lvap_counter_stats)
        return lvap_rate

    def try_change_quantum(self, sta, slc, rate, ratesProm):
        lvap = self.context.lvaps[EtherAddress(sta)]
        wtp = lvap.wtp.addr
        actual_slice = self.context.wifi_slices[str(slc)]
        wtp_quantum = actual_slice.properties['quantum']
        if EtherAddress(wtp) in actual_slice.devices:
            wtp_quantum = actual_slice.devices[wtp]['quantum']
        if wtp_quantum < self.quantum_max and not(self.change_quantum[slc][wtp]):
            self.change_quantum[slc][wtp] = True
            # incrementar 10% del quantum en este wtp para esta slice
            updated_slice = {
                'slice_id': actual_slice.slice_id,
                'properties': {
                    'amsdu_aggregation': actual_slice.properties['amsdu_aggregation'],
                    'quantum': actual_slice.properties['quantum'],
                    'sta_scheduler': actual_slice.properties['sta_scheduler']
                },
                'devices': actual_slice.devices
            }
            addr = EtherAddress(wtp)
            if addr not in updated_slice['devices']:
                actual_quantum = actual_slice.properties['quantum']
                updated_slice['devices'][addr] = {
                    'amsdu_aggregation': actual_slice.properties['amsdu_aggregation'],
                    'quantum': actual_slice.properties['quantum'] + actual_slice.properties['quantum']*self.quantum_increase,
                    'sta_scheduler': actual_slice.properties['sta_scheduler']
                }
            else:
                actual_quantum = updated_slice['devices'][addr]['quantum']
                updated_slice['devices'][addr]['quantum'] = updated_slice['devices'][addr]['quantum'] + updated_slice['devices'][addr]['quantum']*self.quantum_increase
            self.context.upsert_wifi_slice(**updated_slice)
            # Decrementar los quantum para las slices que estan pasadas del rate prometido en el WTP
            self.decreaseQuantum(slc, wtp, ratesProm)
            # escribo en logger
            self.write_log(slc, sta, "Q", lvap.blocks[0].hwaddr.to_str() + "::" + str(actual_quantum) + "->" + str(updated_slice['devices'][addr]['quantum']), "Decrease quantums: " + self.decreased_quantums)
            return True
        else:
            return False

    def decreaseQuantum(self, slc, wtp, ratesProm):
        self.decreased_quantums = ""
        updated_slice = {}
        # para todos los lvaps en el wtp
        for sta in self.context.lvaps:
            lvap = self.context.lvaps[sta]
            if lvap.wtp.addr.to_str() == wtp.to_str():
                lvap_slice = self.getSliceLvap(sta)
                if not(self.change_quantum[lvap_slice][wtp]):
                    promised_rate = ratesProm[lvap_slice]
                    lvap_rate = self.getLVAPRate(sta)
                    # si al menos un lvap tiene mayor rate al prometido y el quantum de esa slice en el wtp es mayor al minimo, le saco recursos
                    if lvap_rate > promised_rate:
                        actual_slice = self.context.wifi_slices[str(lvap_slice)]
                        wtp_quantum = actual_slice.properties['quantum']
                        if EtherAddress(wtp) in actual_slice.devices:
                            wtp_quantum = actual_slice.devices[wtp]['quantum']
                        if wtp_quantum > self.quantum_min:
                            self.change_quantum[lvap_slice][wtp] = True
                            updated_slice = {
                                'slice_id': actual_slice.slice_id,
                                'properties': {
                                    'amsdu_aggregation': actual_slice.properties['amsdu_aggregation'],
                                    'quantum': actual_slice.properties['quantum'],
                                    'sta_scheduler': actual_slice.properties['sta_scheduler']
                                },
                                'devices': actual_slice.devices
                            }
                            addr = EtherAddress(wtp)
                            if addr not in updated_slice['devices']:
                                self.decreased_quantums = self.decreased_quantums + "// S-" + lvap_slice + "--" + str(updated_slice['properties']['quantum']) + "->" + str(updated_slice['properties']['quantum'] - updated_slice['properties']['quantum']*self.quantum_decrease)
                                updated_slice['devices'][addr] = {
                                    'amsdu_aggregation': actual_slice.properties['amsdu_aggregation'],
                                    'quantum': actual_slice.properties['quantum'] - actual_slice.properties['quantum']*self.quantum_decrease,
                                    'sta_scheduler': actual_slice.properties['sta_scheduler']
                                }
                            else:
                                self.decreased_quantums = self.decreased_quantums + "// S-" + lvap_slice + "--" + str(updated_slice['devices'][addr]['quantum']) + "->" + str(updated_slice['devices'][addr]['quantum'] - updated_slice['devices'][addr]['quantum']*self.quantum_decrease)
                                updated_slice['devices'][addr]['quantum'] = updated_slice['devices'][addr]['quantum'] - updated_slice['devices'][addr]['quantum']*self.quantum_decrease
                            self.context.upsert_wifi_slice(**updated_slice)
        return updated_slice

    def ping_pong(self, list_handovers, wtp):
        handovers = list_handovers.copy()
        handovers.reverse()
        res = False
        if len(list_handovers) > 2:
            last_app = next((i for i, item in enumerate(handovers) if item["wtp"] == wtp), None)
            if (type(last_app) == int):
                def wtp_address(x):
                    return x['wtp']
                seq1 = list(map(wtp_address, handovers[:last_app]))
                seq2 = list(map(wtp_address, handovers[(last_app+1):(last_app*2+1)]))
                if (seq1 == seq2):
                    res = True
        return res

    # iperf usa Mbits para medir el rate
    def to_Mbits(self, byte):
        return byte * 8 / 1000000

    # funcion para escribir en un archivo
    def write_log(self, slc, lvap, action, desc, stats):
        file = open("logger.csv", "a")
        timestamp = datetime.utcnow().strftime('%B %d %Y - %H:%M:%S')
        line = timestamp + ";" + slc + ";" + lvap + ";" + action + ";" + desc + ";" + stats
        file.write("\n" + line)
        file.close()

def launch(context, service_id, every=EVERY):
    """ Initialize the module. """

    return NetworkManager(context=context, service_id=service_id, every=every)
