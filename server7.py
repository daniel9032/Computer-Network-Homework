import socket
from time import sleep
import time
import pickle
import math
from random import randint
from threading import Thread, Lock
import _thread
#import numpy as np
from socket import timeout as TimeoutException
SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 5000
STATE_SYN = 0
STATE_SYN_ACK = 1
STATE_ACK = 2
STATE_SS = 0 # slow start
STATE_CA = 1 # congestion avoidence
STATE_FR = 2 # fast recovery
BUF_SIZE = 512*1024
RTT = 20
MSS = 1024
threshold = 64
cwnd = 1
source_address = None
INF = 9999999
mutex = Lock()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((SERVER_ADDRESS, SERVER_PORT))
s.settimeout(0.1)

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
	global cwnd, threshold
	while True:
		with mutex:
			state = 0
			seq = randint(1, 5000)
			while(state < 3):
				start_time = time.time()
				if state == STATE_SYN: 
					try:
						# receive SYN
						packet_byte, source_address = s.recvfrom(BUF_SIZE)
						syn_packet = pickle.loads(packet_byte)
						del packet_byte

						if syn_packet.syn == 1:
							state += 1
							print(f"SYN received! (sequence number: {syn_packet.seq_num})")
					except TimeoutException:
						continue

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

					try:
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
					except TimeoutException:
						state -= 1
						continue

			command_list = ack_packet.data
			if len(command_list) % 2 or len(command_list) == 0:
				print("transmit successfully finished")
				return
			i = 0
			cwnd = 1
			threshold = 32
			data = None
			seq_num = randint(1, 5000)
			ack_num = randint(1, 5000)

			print("----slow start----")
			state = STATE_SS
			while i < len(command_list):
				flag = command_list[i]
				command = command_list[i+1]
				cur_ack_num = 0
				prev_ack_num = 0
				dupACK_count = 0

				if flag == "-f":
					with open(command, "rb") as file:
						vid = file.read()
						gen = chunks(vid, 1024)
						idx = 0
						while idx < (len(vid) // 1024) + 1:
							frag = bytearray()
							packet = None
							for x in range(cwnd):
								if idx + x < (len(vid) // 1024) + 1:
									frag += gen[idx+x]
							if idx + cwnd >= (len(vid) // 1024):
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
							if len(frag) == 4096:
								sleep(0.1)
							else:
								s.sendto(pickle.dumps(packet), source_address)
								print(f"packet sent (sequence number: {packet.seq_num}, ack number: {packet.ack_num}, cwnd: {cwnd}, threshold: {threshold}")

							#while True:
							try:
								dupACK_count_flag = 0
								packet_byte, source_address = s.recvfrom(BUF_SIZE)
								ack_packet = pickle.loads(packet_byte)
								del packet_byte
								print(f"ACK received (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num}")
								cur_ack_num = ack_packet.ack_num
								#print(f"current ack number: {cur_ack_num}, previous ack number: {prev_ack_num}")
								if prev_ack_num == cur_ack_num:
									dupACK_count += 1
									dupACK_count_flag = 1
								prev_ack_num = cur_ack_num
								idx += cwnd
								seq_num += 1
								ack_num += 1
								if state == STATE_SS:
									cwnd *= 2
									if dupACK_count >= 3:
										state = STATE_FR
										threshold = cwnd // 2
										cwnd = threshold + 3
										print("----fast transmit----")
										# resend the packet
										s.sendto(pickle.dumps(packet), source_address)
										print("----fast recovery----")
									elif cwnd >= threshold:
										state = STATE_CA
										print("----congestion avoidence----")
								elif state == STATE_CA:
									if dupACK_count >= 3:
										state = STATE_FR
										threshold = cwnd // 2
										cwnd = threshold + 3
										print("----fast transmit----")
										# resend the packet
										s.sendto(pickle.dumps(packet), source_address)
										print("----fast recovery----")
									cwnd += 1
								elif state == STATE_FR:
									if dupACK_count_flag == 1:
										cwnd *= 2
									else:
										cwnd = threshold
										state = STATE_CA
										print("----congestion avoidence----")
								else:
									raise Exception("invalid state")
								if dupACK_count_flag == 0:
									dupACK_count = 0
								if cwnd > 63:
									cwnd = 63
							except TimeoutException:
								#sleep(0.01)
								pass

					i += 2
				else:
					if flag == "-add" or flag == "-sub" or flag == "-mul" or flag == "-div" or flag == "-pow":
						data = calculate(command)
					elif flag == "-sqrt":
						data = math.sqrt(int(command))
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
						sleep(0.1)
						continue
					s.sendto(pickle.dumps(packet), source_address)
					print(f"packet sent (sequence number: {packet.seq_num}, ack number: {packet.ack_num}, cwnd: {cwnd}, threshold: {threshold})")
					#while True:
					try:
						dupACK_count_flag = 0
						packet_byte, source_address = s.recvfrom(BUF_SIZE)
						ack_packet = pickle.loads(packet_byte)
						del packet_byte
						print(f"ACK received (sequence number: {ack_packet.seq_num}, ack number: {ack_packet.ack_num}")
						cur_ack_num = ack_packet.ack_num
						#print(f"current ack number: {cur_ack_num}, previous ack number: {prev_ack_num}")
						if prev_ack_num == cur_ack_num:
							dupACK_count += 1
							dupACK_count_flag = 1
						prev_ack_num = cur_ack_num
						seq_num += 1
						ack_num += 1
						if state == STATE_SS:
							cwnd *= 2
							if dupACK_count >= 3:
								state = STATE_FR
								threshold = cwnd // 2
								cwnd = threshold + 3
								print("----fast transmit----")
								# resend the packet
								s.sendto(pickle.dumps(packet), source_address)
								print("----fast recovery----")
							elif cwnd >= threshold:
								state = STATE_CA
								print("----congestion avoidence----")
						elif state == STATE_CA:
							if dupACK_count >= 3:
								state = STATE_FR
								threshold = cwnd // 2
								cwnd = threshold + 3
								print("----fast transmit----")
								# resend the packet
								s.sendto(pickle.dumps(packet), source_address)
								print("----fast recovery----")
							cwnd += 1
						elif state == STATE_FR:
							if dupACK_count_flag == 1:
								cwnd *= 2
							else:
								cwnd = threshold
								state = STATE_CA
								print("----congestion avoidence----")
						else:
							raise Exception("invalid state")
						if dupACK_count_flag == 0:
							dupACK_count = 0
						if cwnd > 63:
							cwnd = 63
					except TimeoutException:
						pass
					i += 2
			print("transmit successfully finished")

T = []
for r in range(100):
	t = Thread(target=func, args=tuple())
	T.append(t)
for r in range(100):
	T[r].start()
for r in range(100):
	T[r].join()
