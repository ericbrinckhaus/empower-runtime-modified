from datetime import datetime

from influxdb import InfluxDBClient


client = InfluxDBClient(host='localhost',
                        port=8086,
                        username='root',
                        password='password',
                        timeout=3,
                        database='empower')

client.create_database('empower')

timestamp = datetime.utcnow()
# slices_rates : <id_slice>: <rate>
# lvap_slice : 
#   para cada slice generar un punto, con tag slice igual al id de la slice
#   en campos poner los lvaps: <numero>: <lvap> donde numero no se puede repetir
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
        "tags": {
            "slice": "0"
        },
        "time": timestamp,
        "fields": {
            "0": "D8:CE:3A:8F:0B:4D", 
            "1": "6C:C7:EC:98:16:65", 
            "2": "64:66:B3:8A:52:72",
            "3": "64:66:B3:8A:52:56"
        }
    }
    # {
    #     "measurement": "lvap_slice",
    #     "tags": {
    #         "slice": "1"
    #     },
    #     "time": timestamp,
    #     "fields": {
    #         "0": "64:66:B3:8A:52:56"
    #     }
    # }
]

client.write_points(points)