ECHO SERVER WITH TIMER
==============
This is a simple TCP server implemented with python3.
This server will receive connection at port 9999.
Server will echo data that received from client (with some modification).
Server will also send data to client independently in interval of 2 second.

You can connect generic tcp client to this server, e.g. nc and telnet and
see what they do.

Server need to be run on Linux (because fcntl dan linuxfd) and need
python package ```linuxfd```

HOW TO REPRODUCE BUG #325
==============
1. Setup wifi router (you may use your phone to tether wifi)
2. Connect your computer to wifi
3. Run python3 script to open echo server in port 9999
4. Connect ESP32 to your computer (with USB-to-serial)
5. Open serial terminal to connect to your ESP32
6. Run these AT-Command (some part need to be adjusted to your environment):
	- ```AT+CWQAP```
	- ```AT+CWJAP="[your wifi ssid]","[your wifi password]"```
	- ```AT+CIPMUX=0```
	- ```AT+CIPSTART=0,"TCP","[your computer ip]",9999```
	- ```AT+CIPSEND=5```
7. Stop input anything to serial terminal
8. You will see serial terminal stop sending received data from echo server
