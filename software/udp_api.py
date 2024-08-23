import socket
import sqlite3
from datetime import datetime
import json
from zeroconf import ServiceInfo, Zeroconf
import pandas as pd
import json
from twisted.internet import protocol, reactor


PORT = 1234

# Database settings
DB_FILE = "imu_data.db"

# Create and set up the SQLite database
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS imu_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    position VARCHAR(255),
    ax REAL,
    ay REAL,
    az REAL,
    gx REAL,
    gy REAL,
    gz REAL
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS imu_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    position VARCHAR(255),
    packet_loss REAL,
    sampling_rate REAL
)
""")


conn.commit()

# Set up the UDP server
zeroconf = Zeroconf()


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('192.168.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


IP = get_ip()
print(IP)
info = ServiceInfo("_spirit._udp.local.",
                   name="_spirit._udp.local.",
                   addresses=[socket.inet_aton("192.168.189.245")], port=PORT, server=f"192.168.189.245")
print(info)
zeroconf.register_service(info)




class PacketProtocol(protocol.DatagramProtocol):
    data_list = []
    index_dict = {}
    lost_packet_dict = {}
    timestamp_dict = {}

    def datagramReceived(self, data, addr):
        # Convert payload to json
        #print(data)
        data_json = json.loads(data)
        dt_now = datetime.now()
        timestamp = dt_now.strftime('%Y-%m-%d %H:%M:%S.%f')
        #print(data_json["position"], timestamp)
        self.data_list.append((timestamp, data_json["position"], *data_json["data"][:3], *data_json["data"][3:]))
        if data_json["position"] not in self.index_dict or int(data_json["index"]) < self.index_dict[data_json["position"]]:
            print(int(data_json["index"]))
            self.index_dict[data_json["position"]] = int(data_json["index"])
            self.lost_packet_dict[data_json["position"]] = [0, int(data_json["index"])]
            self.timestamp_dict[data_json["position"]] = [dt_now, self.index_dict[data_json["position"]], self.lost_packet_dict[data_json["position"]][0]]
        self.index_dict[data_json["position"]] += 1
        if self.index_dict[data_json["position"]] % 1000 == 0:
            print(
                f"Current Packet Loss for {data_json['position']}: {round(self.lost_packet_dict[data_json['position']][0] / (self.index_dict[data_json['position']] - self.lost_packet_dict[data_json['position']][1]) * 100, 2)}%")
            dt = dt_now - self.timestamp_dict[data_json["position"]][0]
            current_packets = self.index_dict[data_json['position']] - self.lost_packet_dict[data_json['position']][0]
            past_packets = self.timestamp_dict[data_json['position']][1] - self.timestamp_dict[data_json['position']][2]
            print(f"Current Sampling Rate for {data_json['position']}: {round(1 / (dt.total_seconds() / (current_packets - past_packets)), 2)} Hz")
            self.timestamp_dict[data_json["position"]] = [dt_now, self.index_dict[data_json["position"]], self.lost_packet_dict[data_json["position"]][0]]
            #df = pd.read_sql_query(
            #    f"SELECT timestamp FROM imu_data WHERE position == \'{data_json['position']}\' ORDER BY id DESC LIMIT 200",
            #    sqlite3.connect(DB_FILE))
            #df['timestamp'] = pd.to_datetime(df['timestamp'])
            #df['delta_t'] = (df['timestamp'] - df['timestamp'].shift(-1)).dt.total_seconds()
            #if len(df) > 1:
            #    avg_delta_t = df['delta_t'].iloc[:-1].mean()
            #    frequency = 1 / avg_delta_t
            #    print(f"{data_json['position']} Data Frequency: {frequency:.2f} Hz")
            #else:
            #    print(f"{data_json['position']} Data Frequency: N/A")
        if self.index_dict[data_json["position"]] != int(data_json["index"]) and self.index_dict[data_json["position"]] < int(data_json["index"]):
            self.lost_packet_dict[data_json["position"]][0] += int(data_json['index']) - self.index_dict[data_json["position"]]
            self.index_dict[data_json["position"]] = int(data_json["index"])
        if len(self.data_list) == 100:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            # print("Insert")
            cursor.executemany("""
                INSERT INTO imu_data (timestamp, position, ax, ay, az, gx, gy, gz)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, self.data_list)
            conn.commit()
            conn.close()
            self.data_list = []


class PacketFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return PacketProtocol()


reactor.listenUDP(PORT, interface=IP, protocol=PacketProtocol())
try:
    reactor.run()
except KeyboardInterrupt:
    print("Stopping Server")
finally:
    # Clean up
    zeroconf.unregister_service(info)
    zeroconf.close()
    conn.close()
