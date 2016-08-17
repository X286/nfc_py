# nfc_py
Simple python lib for PN532 chip 

First:

you need to install Crypto (pycrypto), pyserial, binascii.

Second:

This lib work whith PN532 chips. 
Other series chips not tested.

supports: Mifare Classic, Mifare Ultralight, Mifare Ultralight C.

example:
r = PN532 (device='COM2') #for windows (in this case i use MOXA 1130)
by default r= PN532 (device='/dev/ttyAMA0') in RPI
PN532 data exchange by HSU port.
Ex:
r.wakeup()
r.ChipInfo() 
r.card_info()
r.turnOnRF()
r.close_con()
