import socket
from time import sleep
import time
import pickle
import math
from random import randint
from threading import Thread, Lock
import _thread
#import numpy as np
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5000
STATE_SYN = 0
STATE_SYN_ACK = 1
STATE_ACK = 2
BUF_SIZE = 512*1024
RTT = 20
MSS = 1024
threshold = 64*1024
cwnd = 1
source_address = None
INF = 9999999
mutex = Lock()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((SERVER_ADDRESS, SERVER_PORT))

def calculate(command):
	for i in range(len(command)):
		if i != 0:
			if command[i] == '+':
				num1 = int(command[:i])
				num2 = int(command[i+1:])
				return num1 + num2
			if command[i] == '-':
				op_idx = i
				num1 = int(command[:i])
				num2 = int(command[i+1:])
				return num1 - num2
			if command[i] == '/':
				op_idx = i
				num1 = int(command[:i])
				num2 = int(command[i+1:])
				return num1 / num2
			if command[i] == '*' and command[i+1] == '*':
				op_idx = i
				num1 = int(command[:i])
				num2 = int(command[i+2:])
				return num1 ** num2
			if command[i] == '*':
				op_idx = i
				num1 = int(command[:i])
				num2 = int(command[i+1:])
				return num1 * num2

def chunks(l, n):
    n = max(1, n)
    return list(l[i:i+n] for i in range(0, len(l), n))

class TCPPacket:
	def __init__(self, src_port, dst_port, seq_num, ack_num, syn, ack, fin, data=None, window_size=0, chksm=0):
		self.src_port = src_port
		self.dst_port = dst_port
		self.seq_num = seq_num
		self.ack_num = ack_num
		self.chksm = chksm
		self.syn = syn
		self.ack = ack
		self.fin = fin
		self.data = data
		self.window_size = window_size

def func():
	while True:
		with mutex:
			state = 0
			seq = randint(1, 5000)
			while(state < 3):
				start_time = time.time()
				if state == STATE_SYN: 
					# receive SYN
					packet_byte, source_address = s.recvfrom(BUF_SIZE)
					syn_packet = pickle.loads(packet_byte)
					del packet_byte

					if syn_packet.syn == 1:
						state += 1
						print(f"SYN received! (sequence number: {syn_packet.seq_num})")

				elif state == STATE_SYN_ACK:
					# send SYN/ACK
					syn_ack_packet = TCPPacket(src_port=0, 
											   dst_port=0,
											   seq_num=seq,
											   ack_num=syn_packet.seq_num+1,
											   syn=1,
											   ack=1,
											   fin=0,
											   data=None)
					state += 1
					s.sendto(pickle.dumps(syn_ack_packet), source_address)
					print(f"send a packet(SYN/ACK)!")

				elif state == STATE_ACK:
					# receive ACK
					packet_byte, source_address = s.recvfrom(BUF_SIZE)
					ack_packet = pickle.loads(packet_byte)
					del packet_byte

					if ack_packet.ack == 1:
						state += 1
						print(f"ACK received! (sequence number: {ack_packet.seq_num})")
					# If the ack number is incorrect, move to previous state
					if ack_packet.ack_num != (syn_ack_packet.seq_num + 1):
						state -= 1

			command_list = ack_packet.data
			if len(command_list) % 2 or len(command_list) == 0:
				print("transmit successfully finished")
				return
			i = 0
			data = None
			pc = 0
			seq_num = randint(1, 5000)
			ack_num = randint(1, 5000)

			while i < len(command_list):
				flag = command_list[i]
				command = command_list[i+1]

				if flag == "-f":
					with open(command, "rb") as file:
						vid = file.read()
						gen = chunks(vid, 1024)
						idx = 0
						while idx < (len(vid) // 1024) + 1:
							frag = gen[idx]
							pc += 1
							if idx == (len(vid) // 1024):
								packet = TCPPacket(src_port=0, 
												   dst_port=0,
												   seq_num=seq_num,
												   ack_num=ack_num,
												   syn=0,
												   ack=0,
												   fin=1,
												   data=frag)
							else:
								packet = TCPPacket(src_port=0, 
												   dst_port=0,
												   seq_num=seq_num,
												   ack_num=ack_num,
												   syn=0,
												   ack=0,
												   fin=0,
												   data=frag)
							if randint(0, 1) < 1e-6:
								packet.chksm = INF
							s.sendto(pickle.dumps(packet), source_address)
							print(f"packet sent (sequence number: {packet.seq_num}, ack number: {packet.ack_num})")

							idx += 1
							if pc % 2 == 0:
								packet_byte, source_address = s.recvfrom(BUF_SIZE)
								ack_packet = pickle.loads(packet_byte)
								del packet_byte
								print(f"ACK received (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num})")
							seq_num += 1
							ack_num += 1

					i += 2
				else:
					if flag == "-add" or flag == "-sub" or flag == "-mul" or flag == "-div" or flag == "-pow":
						data = calculate(command)
					elif flag == "-sqrt":
						data = math.sqrt(int(command))
					pc += 1
					packet = TCPPacket(src_port=0, 
									   dst_port=0,
									   seq_num=seq_num,
									   ack_num=ack_num,
									   syn=0,
									   ack=0,
									   fin=0,
									   data=data,
									   chksm=0)
					if randint(0, 1) < 1e-6:
						packet.chksm = INF
					s.sendto(pickle.dumps(packet), source_address)
					print(f"packet sent (sequence number: {packet.seq_num}, ack_number: {packet.ack_num})")
					if pc % 2 == 0:
						packet_byte, source_address = s.recvfrom(BUF_SIZE)
						ack_packet = pickle.loads(packet_byte)
						del packet_byte
						print(f"ACK received (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num})")
					i += 2
					seq_num += 1
					ack_num += 1
			print("transmit successfully finished")
			#sleep(0.00001)

t1 = Thread(target=func, args=tuple())
t2 = Thread(target=func, args=tuple())
t3 = Thread(target=func, args=tuple())
t1.start()
t2.start()
t3.start()
t1.join()
t2.join()
t3.join()
