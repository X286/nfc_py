#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial
from Crypto.Cipher import DES3
import binascii
import os


#Basic class
# if you need some options
class NFC (object):
	def __init__ (self, device='/dev/ttyAMA0', baud = 115200,
		parity_ = serial.PARITY_NONE, stop_bits = serial.STOPBITS_ONE, byte_size=serial.EIGHTBITS, time_out=0):
		#ACK header for data recive
		self.Header = bytearray ([0x00,0x00,0xff,0x00,0xff,0x00,0x00,0x00,0xff])
		#time out.
		if time_out != 0:
			self.connectUART = serial.Serial (port=device, baudrate=baud, stopbits=stop_bits, bytesize=byte_size, timeout=time_out)
		else:
			self.connectUART = serial.Serial (port=device, baudrate=baud, stopbits=stop_bits, bytesize=byte_size)

	# manually close connection
	def close_con (self):
		self.connectUART.close()
	
	# Get chip info. if you wanna check chip works right
	def ChipInfo (self):
		self.send_com(0x02, 0xd4, 0x02)
		recived = self.read_com()
		for z, letter in enumerate (recived):
			if z == 0: 
				print '   Integrated Circuit type: ', binascii.hexlify (letter)
			elif z == 1: 
				print '   Circut Version No:', binascii.hexlify (letter)
			elif z == 2: 
				print '   Review No: ', binascii.hexlify (letter)
			elif z == 3: 
				binstr = str(bin(int(binascii.hexlify (letter), base=16))).replace ('0b','')
				if len (binstr) < 8:
					subbin = '0'* (8-len(binstr))
					binstr = subbin + binstr
				print '--------------------------------------------------------------------------------'
				print '| RFU | RFU | RFU | RFU | ISO18092 | ISO/IEC 14443 TypeB | ISO/IEC 14443 TypeA |'
				print '--------------------------------------------------------------------------------'
				conversedstr = ''
				for k,bits in enumerate(binstr):
					if k == 1:
						conversedstr += '|  '+bits + '  '
					elif 1 < k <=4:
						conversedstr += '|  '+bits + '  '
					elif k == 5:
						conversedstr += '|     '+bits+ '    '
					elif k == 6:
						conversedstr += '|         '+bits+ '           '
					elif k == 7:
						conversedstr += '|         '+bits+ '           |'
				print conversedstr
				print '--------------------------------------------------------------------------------'
				print '0 - unsupport, 1 - support'

	#manually open connection
	def opencon (self):
		self.connectUART.close()
		try:
			self.connectUART.open()	
		except:
			self.close_con ()

	#wake up chip
	def wakeup (self):
		self.connectUART.write (bytearray ([0x55,0x55,0x00,0x00,0x00]))
		
	# send command from UserManual (if you want open port, or disable some)
	def send_com (self, commandleng, *data):
		subtrahend_dcs = 0x00
		subtrahend_lcs = 0x100
		command = bytearray ([0x00, 0xff, commandleng, subtrahend_lcs-commandleng])
		dsc_sum = 0x00
		for item in data:
			command.append (item)
			dsc_sum+=item
		command.append(0x100 - dsc_sum % 256)
		
		self.connectUART.write (command)
		
	# after
	def read_com (self):
		usefullrecive = ''
		read_val = self.connectUART.readline(9)
		if read_val.find (self.Header) != -1:
			read_val = self.connectUART.read()
			read_val = self.connectUART.read (int(read_val.encode('hex'), 16)+1)
			usefullrecive = read_val[3:]
			read_val = self.connectUART.read (2)
			return usefullrecive
		else: 
			return '\x00\x00\x01' #000001 - unable to read 


class PN532 (NFC):
	def __init__ (self, device='/dev/ttyAMA0', baud = 115200,
		parity_ = serial.PARITY_NONE, stop_bits = serial.STOPBITS_ONE, byte_size=serial.EIGHTBITS, time_out=0):
		super(PN532, self).__init__(device,baud,parity_,stop_bits,byte_size, time_out)

    #if you want read or write something - turn on antenna
	def turnOnRF (self):
		self.send_com (0x03, 0xD4, 0x14, 0x01)
		self.connectUART.close()
		self.connectUART.open()

	#return data after D#+1,4#+1 command (hex str)
	def card_info (self):
		self.send_com (0x04, 0xD4, 0x4A, 0x01,0x00)
		answer = self.read_com()
		hexanswer = binascii.hexlify (answer)
		print      '---------------------------------------------------------------------'
		print      '| nb_Target | Target Data | SNES_RES(ATQA) | SAK(SEL_RES) | UID len |'
		print      '---------------------------------------------------------------------'
		print      '|   ',hexanswer[0:2],'    |     ',hexanswer[2:4],'    |     ',hexanswer[4:8],'     |    ', hexanswer[8:10],'      |   ', hexanswer[10:12],'  |'
		print      '---------------------------------------------------------------------'
		uids = '|UID(NFCID1)|   '+ hexanswer [-int(hexanswer[10:12],16)*2:]
		if len(uids) < 69:
			uids= uids+' '*(68-len(uids))+'|'
		print uids
		print     '---------------------------------------------------------------------'
		if hexanswer[8:10] == '00':
			print '|          This is Mifare UltraLight or Mifare UltraLightC          |'
		elif hexanswer[8:10] == '08':
			print '|               This is Mifare Classic or Mifare Zero               |'
		elif hexanswer[8:10] == '20':
			print '|                       This is Mifare Plus                         |'
		else:
			print '|                 Something new? Please support me!                 |' 
		print     '---------------------------------------------------------------------'
		return hexanswer

	#return SAK, UID len, UID
	def card_read (self):
		self.send_com (0x04, 0xD4, 0x4A, 0x01,0x00)
		answer = self.read_com()
		return  answer[4], answer[5], answer [-int (binascii.hexlify(answer[5]),16):],
	
	#0x60 - keyA, 0x61 - keyB
	#key - youur auth key
	#addr - auth addr
	# timeout=0.060 - auth correctly works 
	def authMifareClassic (self, keyAorB, addr, *key):
		prepCom  = [0xd4, 0x40, 0x01, keyAorB, addr]
		for byteKey in key:
			prepCom.append(byteKey)
		for uidbyte in self.card_read()[2]:
			prepCom.append (int(uidbyte.encode('hex'), 16))
		self.send_com (0x0f, *prepCom)
		getcode = self.read_com()
		print binascii.hexlify (getcode)

	#00 auth in authMifareClassic ()
	#14 wrong key
	#23 wrong command
	def getMifareClassicBlock (self, comleng, block):
		self.send_com(comleng,0xD4,0x40, 0x01, 0x30, block)
		return self.read_com()


	def authMifareUltralightC (self,key):
		self.send_com (0x05, 0xd4, 0x60, 0x01,0x01,0x00)
		self.read_com()
		self.send_com (0x04, 0xd4,0x42, 0x1A,0x00)
		#auth key must be started  0xAF
		randB = self.read_com()[2:]
		if len (randB) == 8:
			randA = os.urandom (8)
			iv = '\x00\x00\x00\x00\x00\x00\x00\x00'
			firstIteration3DES = DES3.new (key, DES3.MODE_CBC, iv)
			decryptRandB = firstIteration3DES.decrypt(randB)
			rotateB = decryptRandB[1:]+decryptRandB[0]
			uniteRndAandB = randA+rotateB
			decryptRandB = DES3.new (key, DES3.MODE_CBC, randB)
			responce = '\xD4\x42\xAF'+ decryptRandB.encrypt(uniteRndAandB)
			self.send_com (0x13, *bytearray(responce))
			recived = self.read_com()
			if len (recived) > 1: 
				return 0x00 #pass
			else: 
				return 0x02 #shall not pass

		else:
			return 0x01 # something break


#have a fun! don't forget wake up chip!
#
# Ex:
# r= PN532() #work whith windows write something device='COM1' (test: Moxa uport 1130), default - RPI connect
# r.wakeup()
# r.ChipInfo()


'''
r = PN532 (device='COM2')
r.wakeup()
#r.close_con()
r.turnOnRF()
r.ChipInfo()
r.card_info()

# return 00 if auth pass Mifare Ultralight C auth
if r.authMifareUltralightC('BREAKMEIFYOUCAN!') == 0:
	print 'ok'
else:
	print 'not ok'
#mifare classic auth
#r.authMifareClassic(0x60, 0x02, 0xff,0xff,0xff,0xff,0xff,0xff)
#get data in blocks
#print binascii.hexlify (r.getMifareClassicBlock (0x05,0x02))

'''