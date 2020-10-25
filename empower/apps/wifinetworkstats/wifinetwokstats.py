"""WiFi Dynamic slice quantum Primitive."""

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

class NetworkStats(EWiFiApp):
    """WiFi Netork Statistics Primitive.

    This primitive collects the slice statistics.

    Parameters:
        slice_id: the slice to track (optinal, default 0)
        every: the loop period in ms (optional, default 2000ms)

    Example:
        POST /api/v1/projects/52313ecb-9d00-4b7d-b873-b55d3d9ada26/apps
        {
            "name": "empower.apps.wifislicestats.wifislicestats",
            "params": {
                "slice_id": 0,
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

        self.lvap_counters = {}
        for sta in self.context.lvaps:
            sta = sta.to_str()
            self.lvap_counters[sta] = self.counters
        
        self.slice_stats = {}
        for slc in self.context.wifi_slices:
            self.slice_stats[slc] = self.stats

        # Last seen time
        self.last = None
        self.lvap_last = {}

        # My LVAPS 
        # TODO Leer estas lvaps de una base da datos ?
        self.sta = EtherAddress("D8:CE:3A:8F:0B:4D")

    def __eq__(self, other):
        if isinstance(other, HelloWorld):
            return self.every == other.every
        return False

    def to_dict(self):
        """Return JSON-serializable representation of the object."""

        out = super().to_dict()
        out['stats'] = self.slice_stats
        #out['sta'] = self.sta
        out['counters'] = self.lvap_counters

        return out

    def loop(self):
        """Send out requests"""
        for sta in self.context.lvaps:

            lvap = self.context.lvaps[sta]

            msg = Container(length=BIN_COUNTERS_REQUEST.sizeof(),
                            sta=lvap.addr.to_raw())

            lvap.wtp.connection.send_message(PT_BIN_COUNTERS_REQUEST,
                                            msg,
                                            self.handle_lvap_response)

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

        old_tx_bytes = self.lvap_counters[sta]["tx_bytes"]
        old_rx_bytes = self.lvap_counters[sta]["rx_bytes"]

        old_tx_packets = self.lvap_counters[sta]["tx_packets"]
        old_rx_packets = self.lvap_counters[sta]["rx_packets"]

        self.lvap_counters[sta]["tx_bytes"] = self.fill_bytes_samples(tx_samples)
        self.lvap_counters[sta]["rx_bytes"] = self.fill_bytes_samples(rx_samples)

        self.lvap_counters[sta]["tx_packets"] = self.fill_packets_samples(tx_samples)
        self.lvap_counters[sta]["rx_packets"] = self.fill_packets_samples(rx_samples)

        self.lvap_counters[sta]["tx_bps"] = 0
        self.lvap_counters[sta]["rx_bps"] = 0
        self.lvap_counters[sta]["tx_pps"] = 0
        self.lvap_counters[sta]["rx_pps"] = 0

        if self.last:

            delta = time.time() - self.last

            self.lvap_counters[sta]["tx_bps"] = \
                self.update_stats(delta, old_tx_bytes, self.lvap_counters[sta]["tx_bytes"])

            self.lvap_counters[sta]["rx_bps"] = \
                self.update_stats(delta, old_rx_bytes, self.lvap_counters[sta]["rx_bytes"])

            self.lvap_counters[sta]["tx_pps"] = \
                self.update_stats(delta, old_tx_packets, self.lvap_counters[sta]["tx_packets"])

            self.lvap_counters[sta]["rx_pps"] = \
                self.update_stats(delta, old_rx_packets, self.lvap_counters[sta]["rx_packets"])

        # generate data points
        # points = []
        # timestamp = datetime.utcnow()

        # fields = {
        #     "sta": self.sta,
        #     "tx_bytes": self.counters["tx_bytes"],
        #     "rx_bytes": self.counters["rx_bytes"],
        #     "tx_packets": self.counters["tx_packets"],
        #     "rx_packets": self.counters["rx_packets"],
        #     "tx_bps": self.counters["tx_bps"],
        #     "rx_bps": self.counters["rx_bps"],
        #     "tx_pps": self.counters["tx_pps"],
        #     "rx_pps": self.counters["rx_pps"]
        # }

        # tags = dict(self.params)

        # sample = {
        #     "measurement": self.name,
        #     "tags": tags,
        #     "time": timestamp,
        #     "fields": fields
        # }

        # points.append(sample)

        # # save to db
        # self.write_points(points)

        # handle callbacks
        self.handle_callbacks()

        # set last iteration time
        self.last = time.time()


    def handle_slice_stats_response(self, response, *_):
        """Handle WIFI_SLICE_STATS_RESPONSE message."""

        wtp = EtherAddress(response.device)

        slc = str(response.slice_id)

        # update this object
        if wtp not in self.stats:
            self.slice_stats[slc][wtp] = {}

        # generate data points
        points = []
        timestamp = datetime.utcnow()

        for entry in response.stats:

            self.slice_stats[slc][wtp][entry.iface_id] = {
                'deficit_used': entry.deficit_used,
                'max_queue_length': entry.max_queue_length,
                'tx_packets': entry.tx_packets,
                'tx_bytes': entry.tx_bytes,
            }

            tags = dict(self.params)
            tags["wtp"] = wtp
            tags["iface_id"] = entry.iface_id

            sample = {
                "measurement": self.name,
                "tags": tags,
                "time": timestamp,
                "fields": self.slice_stats[slc][wtp][entry.iface_id]
            }

            points.append(sample)

        # save to db
        # self.write_points(points)

        # handle callbacks
        self.handle_callbacks()


def launch(context, service_id, every=EVERY):
    """ Initialize the module. """

    return NetworkStats(context=context, service_id=service_id, every=every)
