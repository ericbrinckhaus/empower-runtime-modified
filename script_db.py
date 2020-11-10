from datetime import datetime

from influxdb import InfluxDBClient


client = InfluxDBClient(host='localhost',
                        port=8086,
                        username='root',
                        password='password',
                        timeout=3,
                        database='tsmanager')

client.create_database('tsmanager')

timestamp = datetime.utcnow()
# slices_rates : <id_slice>: <rate>
# lvap_slice : <id_slice>: [<lvap1>, <lvap2>]
points = [
    {
        "measurement": "slices_rates",
        "tags": {},
        "time": timestamp,
        "fields": {
            "0": 2.0,
            "1": 1.0
        }
    },
    {
        "measurement": "lvap_slice",
        "tags": {},
        "time": timestamp,
        "fields": {
            "0": ["D8:CE:3A:8F:0B:4D", "6C:C7:EC:98:16:65", "64:66:B3:8A:52:72", "64:66:B3:8A:52:72"],
            "1": []
        }
    }
]

client.write_points(points)