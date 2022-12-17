import socket
from time import sleep
import pickle
from random import randint
import sys
from threading import Thread, Lock
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5000
STATE_SYN = 0
STATE_SYN_ACK = 1
STATE_ACK = 2
BUF_SIZE = 512*1024
RTT = 20
MSS = 1024
threshold = 64*1024
cwnd = 1*MSS
source_address = None
INF = 9999999

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class TCPPacket:
	def __init__(self, src_port, dst_port, seq_num, ack_num, syn, ack, fin, data=None, cwnd=MSS, chksm=0):
		self.src_port = src_port
		self.dst_port = dst_port
		self.seq_num = seq_num
		self.ack_num = ack_num
		self.chksm = chksm
		self.syn = syn
		self.ack = ack
		self.fin = fin
		self.data = data
		self.cwnd = cwnd


print("-----------Start 3 way handshaking----------")
seq = randint(1, 5000)
syn_packet = TCPPacket(src_port=0,
					   dst_port=0,
					   seq_num=seq,
					   ack_num=1,
					   syn=1, 
					   ack=0, 
					   fin=0,
					   data=None)
ack_packet = None
state = 0
while (state < 3):
	if state == STATE_SYN:
		# send SYN
		print("send a packet(SYN)!")
		s.sendto(pickle.dumps(syn_packet), (SERVER_ADDRESS, SERVER_PORT))
		state += 1

	elif state == STATE_SYN_ACK:
		# receive SYN/ACK
		packet_byte, source_address = s.recvfrom(BUF_SIZE)
		syn_ack_packet = pickle.loads(packet_byte)
		del packet_byte
		print(f"SYN/ACK received! (sequence number: {syn_ack_packet.seq_num}, ack number: {syn_ack_packet.ack_num})")

		if syn_ack_packet.syn == 1 and syn_ack_packet.ack == 1:
			state += 1

		if syn_ack_packet.ack_num != (syn_packet.seq_num + 1):
			state -= 1

		data = sys.argv[1:]

		ack_packet = TCPPacket(src_port=0,
							   dst_port=0,
							   seq_num=0,
							   ack_num=syn_ack_packet.seq_num+1,
							   syn=0, 
							   ack=1, 
							   fin=0,
							   data=data)

	elif state == STATE_ACK:
		# send ACK
		print("send a packet(ACK)!")
		state += 1
		s.sendto(pickle.dumps(ack_packet), source_address)

print("---------3 way handshaking completed--------")

command_list = sys.argv[1:]
if len(command_list) % 2:
	raise Exception("Invalid command")
data = []
i = 0
pc = 0
while i < len(command_list):
	flag = command_list[i]
	command = command_list[i+1]

	if flag == "-f":
		vid = bytearray()
		while(True):
			packet_byte, source_address = s.recvfrom(BUF_SIZE)
			packet = pickle.loads(packet_byte)
			vid += packet.data
			del packet_byte
			if packet.chksm == INF and packet.fin == 0:
				print(f"packet loss (sequence number: {packet.seq_num}, ack number: {packet.ack_num})")
			else:
				print(f"packet received (sequence number: {packet.seq_num}, ack number: {packet.ack_num})")
			#print(len(vid))

			pc += 1
			if packet.fin != 1:
				if pc % 2 == 0: # send ack every 2 packets received
					ack_packet = TCPPacket(src_port=0,
										   dst_port=0,
										   seq_num=packet.ack_num+1,
										   ack_num=packet.seq_num+1,
										   syn=0, 
										   ack=1, 
										   fin=0,
										   data=None)
					s.sendto(pickle.dumps(ack_packet), source_address)
					print(f"ack sent (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num})")

			elif packet.fin == 1:
				if pc % 2 == 0: # send ack every 2 packets received
					data.append(vid)
					ack_packet = TCPPacket(src_port=0,
										   dst_port=0,
										   seq_num=packet.ack_num+1,
										   ack_num=packet.seq_num+1,
										   syn=0, 
										   ack=1, 
										   fin=0,
										   data=None)
					s.sendto(pickle.dumps(ack_packet), source_address)
					print(f"ack sent (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num})")
				i += 2
				break
	elif flag == "-add" or "-sub" or "-mul" or "-div" or "-pow" or "-sqrt":
		pc += 1
		packet_byte, source_address = s.recvfrom(BUF_SIZE)
		packet = pickle.loads(packet_byte)
		del packet_byte
		if packet.chksm == INF:
			print(f"packet loss (sequence number: {packet.seq_num}, ack number: {packet.ack_num})")
		else:
			print(f"packet received (sequence number: {packet.seq_num}, ack number: {packet.ack_num})")
			data.append(packet.data)
			if pc % 2 == 0:
				ack_packet = TCPPacket(src_port=0,
									   dst_port=0,
									   seq_num=packet.ack_num+1,
									   ack_num=packet.seq_num+1,
									   syn=0, 
									   ack=1, 
									   fin=0,
									   data=None)
				s.sendto(pickle.dumps(ack_packet), source_address)
				print(f"ack sent (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num})")
		i += 2

print("finish receiving")
print("received data:")
for i in data:
	print(i)
