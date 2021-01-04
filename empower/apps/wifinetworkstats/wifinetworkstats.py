"""WiFi Nwtwork Statistics Primitive."""

import time
import math

from datetime import datetime
from datetime import timedelta

from itertools import groupby

from construct import Struct, Int8ub, Int16ub, Int32ub, Int64ub, Bytes, Array
from construct import Container

import empower.managers.ranmanager.lvapp as lvapp

from empower.core.ssid import WIFI_NWID_MAXSIZE
from empower.core.etheraddress import EtherAddress
from empower.managers.ranmanager.lvapp.wifiapp import EWiFiApp
from empower.core.app import EVERY

from empower.apps.wifinetworkstats.lvaprcstats import LvapRCStats


PT_BIN_COUNTERS_REQUEST = 0x82
PT_BIN_COUNTERS_RESPONSE = 0x83

BIN_COUNTERS_REQUEST = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "sta" / Bytes(6),
)
BIN_COUNTERS_REQUEST.name = "bin_counters_request"

COUNTERS_ENTRY = Struct(
    "size" / Int16ub,
    "count" / Int32ub,
)
COUNTERS_ENTRY.name = "counters_entry"

BIN_COUNTERS_RESPONSE = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "sta" / Bytes(6),
    "nb_tx" / Int16ub,
    "nb_rx" / Int16ub,
    "stats" / Array(lambda ctx: ctx.nb_tx + ctx.nb_rx, COUNTERS_ENTRY),
)
BIN_COUNTERS_RESPONSE.name = "bin_counters_response"

PT_WIFI_SLICE_STATS_REQUEST = 0x4C
PT_WIFI_SLICE_STATS_RESPONSE = 0x4D

WIFI_SLICE_STATS_REQUEST = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "ssid" / Bytes(WIFI_NWID_MAXSIZE + 1),
    "slice_id" / Int8ub,
)
WIFI_SLICE_STATS_REQUEST.name = "wifi_slice_stats_request"

SLICE_STATS_ENTRY = Struct(
    "iface_id" / Int32ub,
    "deficit_used" / Int32ub,
    "max_queue_length" / Int32ub,
    "tx_packets" / Int32ub,
    "tx_bytes" / Int32ub,
)
SLICE_STATS_ENTRY.name = "slice_stats_entry"

WIFI_SLICE_STATS_RESPONSE = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "ssid" / Bytes(WIFI_NWID_MAXSIZE + 1),
    "slice_id" / Int8ub,
    "nb_entries" / Int16ub,
    "stats" / Array(lambda ctx: ctx.nb_entries, SLICE_STATS_ENTRY),
)
WIFI_SLICE_STATS_RESPONSE.name = "wifi_slice_stats_response"

PT_WIFI_RC_STATS_REQUEST = 0x80
PT_WIFI_RC_STATS_RESPONSE = 0x81

WIFI_RC_STATS_REQUEST = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "sta" / Bytes(6),
)
WIFI_RC_STATS_REQUEST.name = "wifi_rc_stats_request"

RC_ENTRY = Struct(
    "rate" / Int8ub,
    "prob" / Int32ub,
    "cur_prob" / Int32ub,
    "cur_tp" / Int32ub,
    "last_attempts" / Int32ub,
    "last_successes" / Int32ub,
    "hist_attempts" / Int32ub,
    "hist_successes" / Int32ub
)
RC_ENTRY.name = "rc_entry"

WIFI_RC_STATS_RESPONSE = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "iface_id" / Int32ub,
    "sta" / Bytes(6),
    "nb_entries" / Int16ub,
    "stats" / Array(lambda ctx: ctx.nb_entries, RC_ENTRY),
)
WIFI_RC_STATS_RESPONSE.name = "wifi_rc_stats_response"

PT_UCQM_REQUEST = 0x40
PT_UCQM_RESPONSE = 0x41

PT_NCQM_REQUEST = 0x42
PT_NCQM_RESPONSE = 0x43

CQM_REQUEST = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "iface_id" / Int32ub,
)
CQM_REQUEST.name = "cqm_request"

CQM_ENTRY = Struct(
    "addr" / Bytes(6),
    "last_rssi_std" / Int8ub,
    "last_rssi_avg" / Int8ub,
    "last_packets" / Int32ub,
    "hist_packets" / Int32ub,
    "mov_rssi" / Int8ub
)
CQM_ENTRY.name = "ucqm_entry"

CQM_RESPONSE = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "iface_id" / Int32ub,
    "nb_entries" / Int16ub,
    "entries" / Array(lambda ctx: ctx.nb_entries, CQM_ENTRY)
)
CQM_RESPONSE.name = "cqm_response"

PT_WCS_REQUEST = 0x4A
PT_WCS_RESPONSE = 0x4B

WCS_REQUEST = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "iface_id" / Int32ub,
)
WCS_REQUEST.name = "wcs_request"

WCS_ENTRY = Struct(
    "type" / Int8ub,
    "timestamp" / Int64ub,
    "sample" / Int32ub,
)
WCS_ENTRY.name = "wcs_entry"

WCS_RESPONSE = Struct(
    "version" / Int8ub,
    "type" / Int8ub,
    "length" / Int32ub,
    "seq" / Int32ub,
    "xid" / Int32ub,
    "device" / Bytes(6),
    "iface_id" / Int32ub,
    "nb_entries" / Int16ub,
    "entries" / Array(lambda ctx: ctx.nb_entries, WCS_ENTRY)
)
WCS_RESPONSE.name = "wcs_response"

class NetworkStats(EWiFiApp):
    """WiFi Netork Statistics Primitive.

    This primitive collects the network statistics.

    Parameters:
        every: the loop period in ms (optional, default 2000ms)

    Example:
        POST /api/v1/projects/52313ecb-9d00-4b7d-b873-b55d3d9ada26/apps
        {
            "name": "empower.apps.wifinetworkstats.wifinetworkstats",
            "params": {
                "every": 2000
            }
        }
    """

    def __init__(self, context, service_id, every=EVERY):

        super().__init__(context=context,
                         service_id=service_id,
                         every=every)

        # Register messages
        lvapp.register_message(PT_WIFI_SLICE_STATS_REQUEST, WIFI_SLICE_STATS_REQUEST)
        lvapp.register_message(PT_WIFI_SLICE_STATS_RESPONSE, WIFI_SLICE_STATS_RESPONSE)
        lvapp.register_message(PT_BIN_COUNTERS_REQUEST, BIN_COUNTERS_REQUEST)
        lvapp.register_message(PT_BIN_COUNTERS_RESPONSE, BIN_COUNTERS_RESPONSE)
        lvapp.register_message(PT_WIFI_RC_STATS_REQUEST, WIFI_RC_STATS_REQUEST)
        lvapp.register_message(PT_WIFI_RC_STATS_RESPONSE, WIFI_RC_STATS_RESPONSE)
        lvapp.register_message(PT_UCQM_REQUEST, CQM_REQUEST)
        lvapp.register_message(PT_UCQM_RESPONSE, CQM_RESPONSE)
        lvapp.register_message(PT_NCQM_REQUEST, CQM_REQUEST)
        lvapp.register_message(PT_NCQM_RESPONSE, CQM_RESPONSE)
        lvapp.register_message(PT_WCS_REQUEST, WCS_REQUEST)
        lvapp.register_message(PT_WCS_RESPONSE, WCS_RESPONSE)

        # Data structures
        self.stats = {}
        self.counters = {
            "tx_packets": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "rx_bytes": 0,
            "tx_pps": 0,
            "rx_pps": 0,
            "tx_bps": 0,
            "rx_bps": 0
        }
        self.rates = {}

        self.lvap_counters = {}
        self.lvap_rates = {}
        for sta in self.context.lvaps:
            sta = sta.to_str()
            self.lvap_counters[sta] = self.counters.copy()
            self.lvap_rates[sta] = self.rates.copy()
        
        self.slice_stats = {}
        for slc in self.context.wifi_slices:
            self.slice_stats[slc] = self.stats.copy()

        self.ucqm = {}
        self.ncqm = {}

        # Last seen time
        self.last = None
        self.lvap_last = {}

        # Best prob and rate
        self.best_prob = None
        self.best_tp = None
        self.lvap_best_prob = {}
        self.lvap_best_tp = {}

        # TODO sacar este for y agregalro al de lvaps de arriba
        for sta in self.context.lvaps:
            sta = sta.to_str()
            self.lvap_last[sta] = self.last
            self.lvap_best_prob[sta] = self.best_prob
            self.lvap_best_tp[sta] = self.best_tp

        # Lvap RC Stats classes
        self.rc_stats_classes = {}

        self.channel_stats = {}
        self.agent_ts_ref = {}
        self.runtime_ts_ref = {}

        # Fix duplicate response bug
        self.wcs_seqid = 0

    def __eq__(self, other):
        if isinstance(other, NetworkStats):
            return self.every == other.every
        return False

    def to_dict(self):
        """Return JSON-serializable representation of the object."""

        out = super().to_dict()
        out['stats'] = self.slice_stats
        out['counters'] = self.lvap_counters
        out['rates'] = self.lvap_rates
        out['ucqm'] = self.ucqm
        out['ncqm'] = self.ncqm
        out['channel_stats'] = self.channel_stats

        return out

    def loop(self):
        """Send out requests"""
        for sta in self.context.lvaps:

            lvap = self.context.lvaps[sta]

            # If lvap not in rc classes, create a new one
            sta = sta.to_str()
            if sta not in self.rc_stats_classes:
                self.rc_stats_classes[sta] = LvapRCStats(sta, lvap)

            self.rc_stats_classes[sta].send_request(lvap)

            msg = Container(length=BIN_COUNTERS_REQUEST.sizeof(),
                            sta=lvap.addr.to_raw())

            lvap.wtp.connection.send_message(PT_BIN_COUNTERS_REQUEST,
                                            msg,
                                            self.handle_lvap_response)

            # msg = Container(length=WIFI_RC_STATS_REQUEST.sizeof(),
            #                 sta=lvap.addr.to_raw())

            # lvap.wtp.connection.send_message(PT_WIFI_RC_STATS_REQUEST,
            #                                 msg,
            #                                 self.handle_rc_response)

        self.slc_xid = {}
        for slc in self.context.wifi_slices:
            for wtp in self.wtps.values():

                if not wtp.connection:
                    continue

                msg = Container(length=WIFI_SLICE_STATS_REQUEST.sizeof(),
                                ssid=self.context.wifi_props.ssid.to_raw(),
                                slice_id=int(slc))

                wtp.connection.send_message(PT_WIFI_SLICE_STATS_REQUEST,
                                            msg,
                                            self.handle_slice_stats_response)
                self.slc_xid[msg.xid] = slc

        for wtp in self.context.wtps.values():

            if not wtp.connection:
                continue

            for block in wtp.blocks.values():

                msg = Container(length=CQM_REQUEST.sizeof(),
                                iface_id=block.block_id)

                wtp.connection.send_message(PT_UCQM_REQUEST,
                                            msg,
                                            self.handle_ucqm_response)

                wtp.connection.send_message(PT_NCQM_REQUEST,
                                            msg,
                                            self.handle_ncqm_response)

                msg = Container(length=WCS_REQUEST.sizeof(),
                                iface_id=block.block_id)

                wtp.connection.send_message(PT_WCS_REQUEST,
                                            msg,
                                            self.handle_wcs_response)


    def fill_bytes_samples(self, data):
        """ Compute samples.

        Samples are in the following format (after ordering):

        [[60, 3], [66, 2], [74, 1], [98, 40], [167, 2], [209, 2], [1466, 1762]]

        Each 2-tuple has format [ size, count ] where count is the number of
        packets and size is the size-long (bytes, including the Ethernet 2
        header) TX/RX by the LVAP.
        """

        samples = sorted(data, key=lambda entry: entry.size)
        out = 0

        for entry in samples:
            if not entry:
                continue
            out = out + entry.size * entry.count

        return out

    def fill_packets_samples(self, data):
        """Compute samples.

        Samples are in the following format (after ordering):

        [[60, 3], [66, 2], [74, 1], [98, 40], [167, 2], [209, 2], [1466, 1762]]

        Each 2-tuple has format [ size, count ] where count is the number of
        packets and size is the size-long (bytes, including the Ethernet 2
        header) TX/RX by the LVAP.
        """

        samples = sorted(data, key=lambda entry: entry.size)
        out = 0

        for entry in samples:
            if not entry:
                continue
            out = out + entry.count

        return out

    @classmethod
    def update_stats(cls, delta, last, current):
        """Update stats."""

        stats = 0
        stats = (current - last) / delta

        return stats

    def handle_lvap_response(self, response, *_):
        """Handle BIN_COUNTERS_RESPONSE message."""

        # get lvap mac address
        sta = EtherAddress(response.sta)
        sta = sta.to_str()

        # update this object

        tx_samples = response.stats[0:response.nb_tx]
        rx_samples = response.stats[response.nb_tx:-1]

        old_tx_bytes = self.lvap_counters[sta]["tx_bytes"] if sta in self.lvap_counters else 0.0
        old_rx_bytes = self.lvap_counters[sta]["rx_bytes"] if sta in self.lvap_counters else 0.0

        old_tx_packets = self.lvap_counters[sta]["tx_packets"] if sta in self.lvap_counters else 0.0
        old_rx_packets = self.lvap_counters[sta]["rx_packets"] if sta in self.lvap_counters else 0.0

        self.lvap_counters[sta]["tx_bytes"] = self.fill_bytes_samples(tx_samples)
        self.lvap_counters[sta]["rx_bytes"] = self.fill_bytes_samples(rx_samples)

        self.lvap_counters[sta]["tx_packets"] = self.fill_packets_samples(tx_samples)
        self.lvap_counters[sta]["rx_packets"] = self.fill_packets_samples(rx_samples)

        self.lvap_counters[sta]["tx_bps"] = 0
        self.lvap_counters[sta]["rx_bps"] = 0
        self.lvap_counters[sta]["tx_pps"] = 0
        self.lvap_counters[sta]["rx_pps"] = 0

        if self.lvap_last[sta]:

            delta = time.time() - self.lvap_last[sta]

            self.lvap_counters[sta]["tx_bps"] = \
                self.update_stats(delta, old_tx_bytes, self.lvap_counters[sta]["tx_bytes"])

            self.lvap_counters[sta]["rx_bps"] = \
                self.update_stats(delta, old_rx_bytes, self.lvap_counters[sta]["rx_bytes"])

            self.lvap_counters[sta]["tx_pps"] = \
                self.update_stats(delta, old_tx_packets, self.lvap_counters[sta]["tx_packets"])

            self.lvap_counters[sta]["rx_pps"] = \
                self.update_stats(delta, old_rx_packets, self.lvap_counters[sta]["rx_packets"])

        # generate data points
        points = []
        timestamp = datetime.utcnow()

        fields = {
            "tx_bytes": float(self.lvap_counters[sta]["tx_bytes"]),
            "rx_bytes": float(self.lvap_counters[sta]["rx_bytes"]),
            "tx_packets": float(self.lvap_counters[sta]["tx_packets"]),
            "rx_packets": float(self.lvap_counters[sta]["rx_packets"]),
            "tx_bps": float(self.lvap_counters[sta]["tx_bps"]),
            "rx_bps": float(self.lvap_counters[sta]["rx_bps"]),
            "tx_pps": float(self.lvap_counters[sta]["tx_pps"]),
            "rx_pps": float(self.lvap_counters[sta]["rx_pps"])
        }

        tags = dict(self.params)
        tags["sta"] = sta

        sample = {
            "measurement": 'lvap_counters_stats',
            "tags": tags,
            "time": timestamp,
            "fields": fields
        }

        points.append(sample)

        # save to db
        self.write_points(points)

        # handle callbacks
        self.handle_callbacks()

        # set last iteration time
        self.lvap_last[sta] = time.time()

        # handle rc stats response
        self.handle_class_rc_response(sta)


    def handle_slice_stats_response(self, response, *_):
        """Handle WIFI_SLICE_STATS_RESPONSE message."""

        wtp = EtherAddress(response.device)

        # slc = str(response.slice_id)
        slc = self.slc_xid[response.xid]

        # update this object
        if wtp not in self.stats:
            self.slice_stats[slc][wtp] = {}

        # generate data points
        points = []
        timestamp = datetime.utcnow()

        for entry in response.stats:

            self.slice_stats[slc][wtp][entry.iface_id] = {
                'deficit_used': float(entry.deficit_used),
                'max_queue_length': float(entry.max_queue_length),
                'tx_packets': float(entry.tx_packets),
                'tx_bytes': float(entry.tx_bytes),
            }

            tags = dict(self.params)
            tags["slc"] = slc
            tags["wtp"] = wtp
            tags["iface_id"] = entry.iface_id

            sample = {
                "measurement": "wifi_slice_stats",
                "tags": tags,
                "time": timestamp,
                "fields": self.slice_stats[slc][wtp][entry.iface_id]
            }

            points.append(sample)

        # save to db
        self.write_points(points)

        # handle callbacks
        self.handle_callbacks()

    def handle_rc_response(self, response, *_):
        """Handle WIFI_RC_STATS_RESPONSE message."""

        # get lvap mac address
        sta = EtherAddress(response.sta)
        sta = sta.to_str()

        lvap = self.context.lvaps[sta]

        # update this object
        self.lvap_rates[sta] = {}
        self.lvap_best_prob[sta] = None
        self.lvap_best_tp[sta] = None

        # generate data points
        points = []
        timestamp = datetime.utcnow()

        for entry in response.stats:

            rate = entry.rate if lvap.ht_caps else entry.rate / 2.0

            fields = {
                'prob': entry.prob / 180.0,
                'cur_prob': entry.cur_prob / 180.0,
                'cur_tp': entry.cur_tp / ((18000 << 10) / 96) / 10,
                'last_attempts': entry.last_attempts,
                'last_successes': entry.last_successes,
                'hist_attempts': entry.hist_attempts,
                'hist_successes': entry.hist_successes,
            }

            tags = dict(self.params)
            tags["rate"] = rate

            self.lvap_rates[sta][rate] = fields

            sample = {
                "measurement": self.name,
                "tags": tags,
                "time": timestamp,
                "fields": fields
            }

            points.append(sample)

            # compute statistics
            self.lvap_best_prob[sta] = \
                max(self.rates.keys(), key=(lambda key: self.rates[key]['prob']))

            self.lvap_best_tp[sta] = \
                max(self.lvap_rates[sta].keys(), key=(lambda key: self.lvap_rates[sta][key]['cur_tp']))

            # save to db
            # self.write_points(points)

            # handle callbacks
            self.handle_callbacks()

    def handle_class_rc_response(self, sta):
        # update this object
        self.lvap_rates[sta] = {}
        self.lvap_best_prob[sta] = None
        self.lvap_best_tp[sta] = None

        resp = self.rc_stats_classes[sta].to_dict()
        
        self.lvap_rates[sta] = resp['rates']
        self.lvap_best_prob[sta] = resp['best_prob']
        self.lvap_best_tp[sta] = resp['best_tp']

        # generate data points
        points = []
        timestamp = datetime.utcnow()

        for rate in resp['rates'].keys():
            
            tags = dict(self.params)
            tags["sta"] = sta
            tags["rate"] = rate

            sample = {
                "measurement": "lvap_rc_stats",
                "tags": tags,
                "time": timestamp,
                "fields": resp['rates'][rate]
            }

            points.append(sample)

        # save to db
        self.write_points(points)

    def handle_ucqm_response(self, response, wtp, _):
        """Handle UCQM_RESPONSE message."""

        block = wtp.blocks[response.iface_id]
        block.ucqm = {}

        # generate data points
        points = []
        timestamp = datetime.utcnow()

        for entry in response.entries:
            addr = EtherAddress(entry['addr'])
            block.ucqm[addr] = {
                'addr': addr,
                'last_rssi_std': entry['last_rssi_std'],
                'last_rssi_avg': entry['last_rssi_avg'],
                'last_packets': entry['last_packets'],
                'hist_packets': entry['hist_packets'],
                'mov_rssi': entry['mov_rssi']
            }

            tags = dict(self.params)
            tags["wtp"] = wtp.addr
            tags["block_id"] = response.iface_id
            tags["addr"] = addr

            sample = {
                "measurement": 'ucqm_rssi',
                "tags": tags,
                "time": timestamp,
                "fields": block.ucqm[addr]
            }

            points.append(sample)

        # save to db
        self.write_points(points)

        if wtp.addr not in self.ucqm:
            self.ucqm[wtp.addr] = {}
        self.ucqm[wtp.addr][block.block_id] = block.ucqm
        self.ucqm[wtp.addr][block.block_id]['timestamp'] = timestamp

        # handle callbacks
        self.handle_callbacks()

    def handle_ncqm_response(self, response, wtp, _):
        """Handle NCQM_RESPONSE message."""

        block = wtp.blocks[response.iface_id]
        block.ncqm = {}

        for entry in response.entries:
            addr = EtherAddress(entry['addr'])
            block.ncqm[addr] = {
                'addr': addr,
                'last_rssi_std': entry['last_rssi_std'],
                'last_rssi_avg': entry['last_rssi_avg'],
                'last_packets': entry['last_packets'],
                'hist_packets': entry['hist_packets'],
                'mov_rssi': entry['mov_rssi']
            }

        if wtp.addr not in self.ncqm:
            self.ncqm[wtp.addr] = {}
        self.ncqm[wtp.addr][block.block_id] = block.ncqm
        self.ucqm[wtp.addr][block.block_id]['timestamp'] = datetime.utcnow()

        # handle callbacks
        self.handle_callbacks()

    def handle_wcs_response(self, response, wtp, *_):
        """Handle WCS_RESPONSE message."""

        if response.seq == self.wcs_seqid:
            return
        else:
            self.wcs_seqid = response.seq 

        block_id = response.iface_id

        # init data structures for the incoming block
        if block_id not in self.channel_stats:
            self.channel_stats[block_id] = {}
            self.agent_ts_ref[block_id] = 0
            self.runtime_ts_ref[block_id] = None

        # pre-processing: ed = ed - (rx + tx)
        # tx: 0:100, rx: 100:200, ed: 200:300
        # TODO ver si hay que usar esto o no
        for index in range(200, 300):
            response.entries[index].sample -= \
                response.entries[index - 100].sample + \
                response.entries[index - 200].sample

        # at the beginning, create the map between runtime and agent timestamps
        # entry[0] = stat type [0, 1, 2] -> [tx, rx, ed]
        # entry[1] = agent timestamp
        # entry[2] = stat value
        if self.agent_ts_ref[block_id] == 0:
            for entry in response.entries:
                if entry.timestamp > self.agent_ts_ref[block_id]:
                    self.agent_ts_ref[block_id] = entry.timestamp
            self.runtime_ts_ref[block_id] = datetime.utcnow()

        self.channel_stats[block_id] = []

        for entry in response.entries:

            stat_type = ["tx", "rx", "ed"][entry.type]
            ts_delta = timedelta(microseconds=(entry.timestamp -
                                               self.agent_ts_ref[block_id]))
            value = entry.sample / 180.0

            # skip invalid samples
            # TODO ver si esto esta bien
            if value == None or abs(value) == 200 or abs(value) == 600:  # tx, rx: 200; ed: 200 - (200 + 200)
                continue

            sample = {
                "type": stat_type,
                "time": self.runtime_ts_ref[block_id] + ts_delta,
                "value": value
            }

            self.channel_stats[block_id].append(sample)

        # update wifi_stats module
        block = wtp.blocks[block_id]
        block.channel_stats = self.channel_stats[block_id]

        # save samples
        sorted_samples = sorted(block.channel_stats,
                                key=lambda x: x["time"].timestamp())
        samples = []

        for tstamp, sample_fields in groupby(sorted_samples,
                                             lambda x: x["time"].timestamp()):

            fields = {}

            for item in sample_fields:
                fields[item["type"]] = item["value"]

            tags = dict(self.params)
            tags["wtp"] = wtp.addr
            tags["block_id"] = block_id

            sample = {
                "measurement": "wifi_channel_stats",
                "tags": tags,
                "time": datetime.fromtimestamp(tstamp),
                "fields": fields
            }
            samples.append(sample)

        self.write_points(samples)

        # handle callbacks
        self.handle_callbacks()

def launch(context, service_id, every=EVERY):
    """ Initialize the module. """

    return NetworkStats(context=context, service_id=service_id, every=every)
