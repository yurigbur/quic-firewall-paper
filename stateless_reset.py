import socket, sys, time, secrets
from struct import *


source_ip = '127.0.0.1'
dest_ip = '127.0.0.1'

# Stateless Reset Payload
def buildQUIC():

    #Stateless Reset {
    #     Fixed Bits (2) = 1,
    #     Unpredictable Bits (38..),
    #     Stateless Reset Token (128),
    #   }


    quic_fbits = 0x40
    quic_ubits = secrets.token_bytes(20)
    quic_rtok = bytearray(b'\xba') * 16

    return pack('!B20s16s', quic_fbits, quic_ubits, quic_rtok)


def udpChecksum(data):
    checksum = 0
    data_len = len(data)
    if (data_len % 2):
        data_len += 1
        data += pack('!B', 0)
    
    for i in range(0, data_len, 2):
        w = (data[i] << 8) + (data[i + 1])
        checksum += w

    checksum = (checksum >> 16) + (checksum & 0xFFFF)
    checksum = ~checksum & 0xFFFF
    return checksum


# UDP Header
def buildUDP(payload):
    udp_sport = int(sys.argv[1])
    udp_dport = int(sys.argv[2])
    udp_len = 8 + len(payload)

    # Pseudoheader for Checksum
    pseudo_header = pack('!4s4sBBH', socket.inet_aton(source_ip), socket.inet_aton(dest_ip), 0, socket.IPPROTO_UDP, udp_len)
    udp_header = pack('!HHHH', udp_sport, udp_dport, udp_len, 0)
    udp_csum = udpChecksum(pseudo_header + udp_header + payload)

    return pack('!HHHH', udp_sport, udp_dport, udp_len, udp_csum) 


# IP Header
def buildIP():

    ip_ihl = 5
    ip_ver = 4
    ip_tos = 0
    ip_tot_len = 0
    ip_id = 1337
    ip_frag_off = 0
    ip_ttl = 255
    ip_proto = socket.IPPROTO_UDP
    ip_check = 0
    ip_saddr = socket.inet_aton(source_ip)
    ip_daddr = socket.inet_aton(dest_ip)

    ip_ihl_ver = (ip_ver << 4) + ip_ihl
    
    return pack('!BBHHHBBH4s4s' , ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)


def main():

	if len(sys.argv) != 3:
		print(f"Usage: {sys.argv[0]} <sport> <dport>")
		return

    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    print("Building Payload")
    rst_payload = buildQUIC()
    print("\t",rst_payload)
    print("Building UDP Header")
    udp_header = buildUDP(rst_payload) 
    print("\t",udp_header)
    print("Building IP Header")
    ip_header = buildIP()
    print("\t",ip_header)


    packet = ip_header + udp_header + rst_payload
    print("Sending payload 5 times")
    for i in range(0,5):
        s.sendto(packet, (dest_ip, 0 ))

    print("Finished")
    

if __name__ == "__main__":
    main()

