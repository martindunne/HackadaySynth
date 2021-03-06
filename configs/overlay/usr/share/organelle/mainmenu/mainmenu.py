#!/usr/bin/python
'''
had to transfer 
libncurses.so.5    libncursesw.so.5.9  libpanelw.so.5    libtinfo.so.5.9
libncurses.so.5.9  libpanel.so.5       libpanelw.so.5.9
libncursesw.so.5   libpanel.so.5.9     libtinfo.so.5

from a debian install of python, not sure why but prefresh() errors and whatnot
based on newpad and anything pad related

now everything seems to work as long as i update the pad for the screensize


'''
import curses, curses.panel
import socket, OSC, threading, subprocess
import time

import locale
locale.setlocale(locale.LC_ALL,'') #unicode support?

localhost = "127.0.0.1"
sendPD    =  4001
receivePD = localhost, 4000
receiveSer =localhost, 3998
sendSer   =  3999
sendAux = 4002 #needed for interactive aux programs wrt encoder

def bash(command):
	'''
	any bash command output in array
	'''
	return subprocess.check_output(['/bin/bash','-c',command]).strip('\n').split('\n')#could be /bash 

def runOnTTY(tty, cmd):
	'''
	directly open tty and run command on it
	tty 5 and 6 both start /bin/sh, check /etc/inittab
	'''
	import sys,os,fcntl,termios
	fd = os.open("/dev/" + tty, os.O_RDWR)
	for i in range(len(cmd)):
	   fcntl.ioctl(fd, termios.TIOCSTI, cmd[i])
	fcntl.ioctl(fd, termios.TIOCSTI, '\n')
	os.close(fd)


class panelGen:
	 #41 cols, 14 rows originally
	def __init__(self, name, stdscr, columns=320, rows=240, \
				bgcolor=0, subpanels=0, \
				font='/usr/share/organelle/configs/LatArCyrHeb-19.psfu.gz', pixels=0):
		self.name = name
		self.stdscr = stdscr
		self.columns = columns
		self.rows = rows
		self.bgcolor = bgcolor
		self.subpanels = subpanels
		self.text = 1
		self.pixels= pixels
		self.on='1'
		self.off='0'
		self.font= font#/usr/share/consolefonts/LatArCyrHeb-19.psfu.gz -16 
		self.colors = ['white','black','red','green','yellow','blue','purple','cyan']
		#self.window = curses.newwin(self.rows, self.columns,0,0) #check out newpad and refresh() options in curses
		self.window = curses.newpad(self.rows, self.columns)
		self.window.erase()
		#self.panel = curses.panel.new_panel(self.window)
		self.fullinfo = self.name, self.window,  self.rows, self.columns, self.text
		command = "setfont " + self.font + "<> /dev/tty4 >&0 2>&1"
		subprocess.call(command, shell=True)
		subprocess.call("chvt 4", shell=True) #assumes fbtft_ili9341 connected
		bash('stty rows 240 cols 320')
	def changeFont(self):
		command = 'setfont ' + self.font + ' <> /dev/tty4 >&0 2>&1 \n'#really need to change it for pixel font
		bash(command)
	def window(self):
		return self.window
	def makeWindow(self, cols, rows):
		self.window = curses.newpad(cols, rows) 
	def show(self):
		self.window.redrawwin()
	def update(self):
		self.window.refresh(0,0,0,0,11,39) #normal windows are this big using def font
	def updateG(self):
		self.window.refresh(0,0,0,0,239,319) #graphics window is this big and needs its own call
	def erase(self):
		self.window.erase()
	def info(self):
		return self.fullinfo
	def columns(self):
		return self.columns
	def rows(self):
		return self.rows
	def hide(self):
		self.panel.hide()
	def string( self, string, y, x, color=2,attributes=curses.A_BOLD ):
		try:
			self.window.addstr( y, x, string, attributes | curses.color_pair(color))
		except:
			pass
	def delete( self, length, y, x ) :
		blankline = ""
		for b in xrange(length):
			blankline += " "
		self.window.addstr( y, x, blankline )
	def highlight( self,  line):
		self.window.chgat(line, 0, -1, curses.A_REVERSE)
	def drawPixel(self, x, y, color):
		try:
			self.window.addstr( y, x, '1', curses.color_pair(color))
		except:
			pass
	def eraseEntireGraphics(self):
		for x in self.columns:
			for y in self.rows:
				self.window.addstr(y,x,'0',)
	def drawLine(self, startx, starty, endx, endy,color=2): #this only sorta works?
		xdist = endx - startx #100
		ydist = endy - starty #0
		if(abs(ydist)  > abs(xdist) or ydist == 0 )and xdist != 0: #x is shortest but not zero
			if startx > endx:
				_counter = -1 #range needs -1 to count down
			else:
				_counter = 1
			if xdist == 0:
				_skips = 1
			else:
				_skips = ydist / (xdist*1.0) #could divide by zero DUMMY
			for index, lines in enumerate(range(startx,endx+1, _counter)):
			#for index, lines in enumerate(range(starty,endy+1, _counter)):
				self.window.addstr(int(starty+(_skips*index*_counter)), lines, '1', curses.color_pair(color))
		elif abs(xdist) >= abs(ydist) or xdist == 0:
			if starty > endy:
				_counter = -1
			else:
				_counter = 1
			if ydist == 0:
				_skips = 1
			else:
				_skips = xdist / (ydist*1.0) #div/0
			for index, lines in enumerate(range(starty,endy+1, _counter)):
			#for index, lines in enumerate(range(startx,endx+1, _counter)):
				self.window.addstr(lines, int(startx+(_skips*index*_counter)), '1', curses.color_pair(color))
	def drawCircle(self, xorigin, yorigin, radius, color):
		import math
		theta = 1
		while theta < 360:
			curx = int(xorigin + radius*(math.cos(theta)))
			cury = int(yorigin + radius*(math.sin(theta)))
			self.drawPixel( curx, cury, color)
			theta += 1
	def drawBox(self, x,y,width,height,color):
		self.drawLine(x,y,x+width,y,color)#top bar
		self.drawLine(x,y,x,y+height,color)#left bar
		self.drawLine(x+width,y,x+width,y+height,color)#right bar
		self.drawLine(x,y+height,x+width,y+height,color)#bottom bar
	def drawFill(self, x,y,width,height,color):
		a = ''
		for i in range(width):
			a+= '1'
		for piece in range(height):
			self.window.addstr(y+piece,x,a,curses.color_pair(color))
	def drawWaveform(self, fuck): #last item in array is color
		fuck[0] = 'garbage'
		array = fuck[1:-2]
		color = fuck[-1]
		prevx = 0
		prevy = 0
		for index, line in enumerate(array):
			self.drawLine(prevx, 239-(line % 240 ) ,index+1, 239-(fuck[index+1]) % 240, color % 9 )
			prevx = index+1
			prevy = line

 
stdscr = curses.initscr()
aux = panelGen('aux', stdscr) #needs to be called after initscr so we pass the screen around
oled = panelGen('oled', stdscr) #standard patch output screen
graphics = panelGen('graphics', stdscr, columns = 320, rows = 240, font = '/usr/share/organelle/configs/pixel.psfu', pixels=1) #'1' is pixel, '0' is blank#
#graphics = rawScreen('graphics',stdscr)
dummy = panelGen('dummy',stdscr)
menu = panelGen('menu', stdscr) #needs own menu screen to not be overwrit

'''
 ____   ___  __  __ _____ 
/ ___| / _ \|  \/  | ____|
\___ \| | | | |\/| |  _|  
 ___) | |_| | |  | | |___ 
|____/ \___/|_|  |_|_____|
                          
__     ___    ____  ___    _    ____  _     _____ ____  
\ \   / / \  |  _ \|_ _|  / \  | __ )| |   | ____/ ___| 
 \ \ / / _ \ | |_) || |  / _ \ |  _ \| |   |  _| \___ \ 
  \ V / ___ \|  _ < | | / ___ \| |_) | |___| |___ ___) |
   \_/_/   \_\_| \_\___/_/   \_\____/|_____|_____|____/ 

'''


buttonPressed = 0 #timer for button held down > 5 seconds, trigger shutdown
encoderEvent = time.time() -5  #encoder event paused subpatch menu
patchRunning = 0
pixel = 0
ORIGTTY = curses.savetty()
ORIGPROG = curses.def_shell_mode()
def invertline(a,t,d,s):
	menu.highlight(d[0])
	menu.update()
	menu.show()
def graphicsUpdate(a,t,d,s):
	#bash('setfont /usr/share/organelle/configs/pixel.psfu') #or you'll error out
	graphics.updateG() #push new pad to screen
	#graphics.show()
	
def dummyShow():
	dummy.erase()
	dummy.updateG()
	dummy.show()
def graphicsWave(a,t,d,s):
	global pixel
	pixel = 1
	graphics.drawWaveform(d)
	#graphics.updateG()
	#graphics.show()

# oscsend 127.0.0.1 3998 /oled/line/1 s "HELLO WORLDS"
#drawCircle(self, xorigin, yorigin, radius, color):
def graphicsFill(a,t,d,s):
	global pixel
	pixel = 1
	graphics.drawFill(d[1],d[2],d[3],d[4],d[5])
	#graphics.updateG()
	#graphics.show()
def graphicsBox(a, t, d, s):
	global pixel
	pixel = 1
	graphics.drawBox(d[1],d[2],d[3],d[4],d[5])
	#graphics.updateG()
	#graphics.show()
def graphicsCircle(addr, tags, data, source):
	global pixel
	pixel = 1
	graphics.drawCircle(data[1], data[2], data[3],data[4])
	#graphics.updateG()
	#graphics.show()

def graphicsLine(addr, tags, data, source):
	global pixel
	pixel = 1
	#data[0] is null here
	#startx, starty, endx, endy, color
	graphics.drawLine(data[1],data[2],data[3],data[4],data[5])
	#graphics.updateG()
	#graphics.show()

def pixel(addr, tags, data, source):
	#dummyShow()
	global pixel
	pixel = 1
	graphics.drawPixel(data[1],data[2], data[3])
	#graphics.updateG()
	#graphics.show()


def setPixelScreen(addr, tags, data, source):
	global pixel
	#global curses
	pixel = 1
	curses.resizeterm(240, 320)
	#graphics.makeWindow(320,240)
	#graphics.changeFont()
	bash('setfont /usr/share/organelle/configs/pixel.psfu')
	graphics.eraseEntireGraphics()
	#graphics.updateG()
	#graphics.show()

def screenLine(addr, tags, data, source): #/oled/line/1-5 and some string shit
	#global pixel
	#if pixel == 1:
	#	oled.changeFont()
	#	pixel = 0
	global encoderEvent
	if (time.time() - encoderEvent) < 5:
		return
	oled.changeFont()
	line = int(addr.split("/")[-1])+1  #last number in OSC address
	temp=''
	for piece in data:
		temp+=str(piece)+' '
	oled.delete( 41, line, 0)
	oled.string( temp, line, 0)
	oled.update()
	oled.show()
	

def auxLine(addr, tags, data, source):
	line = int(addr.split("/")[-1]) #last number in OSC address
	temp=''
	for piece in data:
		temp+=str(piece)+' '
	aux.delete( 41, line, 0)
	aux.string( temp, line, 0)
	aux.update()
	aux.show()
	aux.changeFont()

def setScreen(addr, tags, data, source):
	aux.show()

def shutdown(addr, tags, data, source):
	curses.nocbreak()
	stdscr.keypad(0)
	curses.echo()
	curses.endwin()
	POSC.join()
	SOSC.join()

	quit()

def erase(addr, tags, data, source):
	oled.erase()
	oled.update()

def eraseAux(addr, tags, data, source):
	aux.erase()

def vuMeter(addr, tags, data, source): # /oled/vumeter iiii ADCL ADCR OUTL OUTR
	#but do it with lines 0 and 1 as either # or - 
	global pixel
	if pixel == 1:
		return
	global encoderEvent
	if (time.time() - encoderEvent) < 5:
		return
	on = '#'
	off = '-'
	IR=''
	IL=''
	OR=''
	OL=''
	for x in range(18):
		if(data[0]>x):
			IL += on
		else:
			IL += off
		if(data[1]>x):
			IR += on
		else:
			IR += off
		if(data[2]>x):
			OL += on
		else:
			OL += off
		if(data[3]>x):
			OR += on
		else:
			OR += off
	oled.delete(41,0,0)
	oled.delete(41,1,0)
	oled.string('I',0,0)
	oled.string('I',1,0)
	oled.string('O',0,41/2)
	oled.string('O',1,41/2)
	oled.string(IR,0,1)
	oled.string(IL,1,1)
	oled.string(OR,0,(41/2)+1)
	oled.string(OL,1,(41/2)+1)
	oled.update()
	oled.show()

def initClientComport(ip, port):
	'''needs to be a separate global'''
	global comport
	comport = OSC.OSCClient()
	comport.connect( (ip,port) )

def initClientPD(ip, port):
	global pd
	pd = OSC.OSCClient()
	pd.connect( (ip,port) )

def initClientAux(ip, port):
	global auxclient
	auxclient = OSC.OSCClient()
	auxclient.connect( (ip, port) )

initClientAux( localhost, sendAux )
initClientComport ( localhost, sendSer )
initClientPD( localhost, sendPD ) 

def sendOSCComport( address='/print', data=[] ):
	m = OSC.OSCMessage()
	m.setAddress(address)
	for d in data:
		m.append(d)
	comport.send(m)

def sendOSCPD( address='/print', data=[] ):
	m = OSC.OSCMessage()
	m.setAddress(address)
	for d in data:
		m.append(d)
	pd.send(m)

def sendOSCAux( address='/print', data=[] ):
	m = OSC.OSCMessage()
	m.setAddress(address)
	for d in data:
		m.append(d)
	auxclient.send(m)


def led(addr, tags, data, source):
	#changes LED state from PD program
	sendOSCComport("/led",data)

def keys(addr, tags, data, source):
	#send keys from STM32 to PD
	#while navigating menu patch is not open yet
	try:
		sendOSCPD("/key", data)
	except:
		pass

def knobs(addr, tags, data, source):
	#send knobs from STM32 to PD
	#while navigating menu patch is not open yet
	try:
		sendOSCPD("/knobs", data)
	except:
		pass

def quitpd(addr, tags, data, source):
	sendOSCPD("/quitpd",1)

auxsub = 0
patchsub = 0

def enableAuxSub(addr, tags, data, source):
	if data[0] == 1:
		auxsub = 1
	else:
		auxsub = 0

def enablePatchSub(addr, tags, data, source):
	if data[0] == 1:
		patchsub = 1
	else:
		patchsub = 0
#######################################################

def x11Forwarding():
	sshSessions = bash('pgrep ssh') #always going to be 0 as sshd daemon
	if len(sshSessions) > 1: #another ssh daemon has begun
		return 1 #you can forward on x11
	return 0 #nope


class MenuItem:
	def __init__(self, name="THEMENU", userDir="/root/patches/", \
					scriptDir="/usr/share/organelle/scripts/",   \
					rows=12):
			self.name = name
			self.userDir = userDir
			self.scriptDir = scriptDir
			self.index = 0
			self.rows = rows
			self.Mother="/usr/share/organelle/mother/mother.pd"
			self.setPid = 'screen -S chamble -X stuff "echo `echo $\!` > /run/patch.pid & \n"'
			self.chrt = 'screen -S chamble -X stuff "chrt -rp 99 `cat /run/patch.pid` & \n"'
			self.taskset = 'screen -S chamble -X stuff "taskset -p 0x8 `cat /run/patch.pid` & \n"'
			import os
			self.menuItems = []
			for x in sorted(os.listdir(self.scriptDir+'.')):
				self.menuItems.append(x)
			self.scriptsEnd = len(self.menuItems)  #anything above this entry is a bash script
			for x in sorted(os.listdir(self.userDir+'.')):
				self.menuItems.append(x)
			self.menuEnd = len(self.menuItems) -1 #anything past this, loop back to the top
			self.currentMenu = []
			for x in xrange(12):
				self.currentMenu.append(self.menuItems[x])
			self.currentMenuBegin=0
			self.currentMenuEnd=11
	def returnScreen(self):
		temp = []
		
		if self.menuItems[self.index] not in self.currentMenu:
			self.currentMenu = []
			if self.currentMenuEnd < self.index: #actual item is one further in the array
				for x in range(self.currentMenuBegin+1, self.currentMenuEnd+2):
					self.currentMenu.append(self.menuItems[x])
				self.currentMenuBegin+=1
				self.currentMenuEnd+=1
			if self.currentMenuBegin > self.index: #actual item is one behind the current menu
				for x in range(self.currentMenuBegin-1, self.currentMenuEnd):
					self.currentMenu.append(self.menuItems[x])
				self.currentMenuBegin-=1
				self.currentMenuEnd-=1
		for i, item in enumerate(self.currentMenu):
			temp.append(item)
		return temp
	def generateMenu(self, bashDir,  patchDir):
		self.menuItems = []
		for x in os.listdir(bashDir+'.'):
			self.menuItems.append(x)
		self.scriptsEnd = len(self.menuItems)  #anything above this entry is a bash script
		for x in os.listdir(self.patchDir+'.'):
			self.menuItems.append(x)
		self.menuEnd = len(self.menuItems) -1 #anything past this, loop back to the top
		self.currentMenu = []
		for x in xrange(12):
			self.currentMenu.append(self.menuItems[x])
		self.currentMenuBegin=0 #12 lines on screen
		self.currentMenuEnd=11
		#generateMenu('/usr/share/organelle/extra/', self.userDir+self.menuItems[self.index]+'/')
	def returnIndex(self):
		return self.index()
	def activeEntry(self):
		return self.menuItems[self.index]
	def moveDown(self):
		if self.index == 0: #dont go before the begining of the list
			pass
		else:
			self.index -= 1
	def moveUp(self):
		if self.index == self.menuEnd: #dont go past the end of the list
			pass
		else:
			self.index += 1
	def execute(self):
		if self.index >=0 and self.index < self.scriptsEnd: #if you are in script command 
			#try:
			command =  str(self.scriptDir+self.menuItems[self.index])
			bash(command)
			'''
			except:
				menu.erase()
				tricks = menuList.returnScreen()
				for y,d in enumerate(tricks): #y is index, d is entry
					menu.delete(menu.columns, y,0)
					if menuList.activeEntry() == d:
						menu.string(d,y,0 ,color=0, attributes=curses.A_BOLD | curses.A_UNDERLINE )
					else:
						menu.string(d,y,0)
				menu.update()
				menu.show()
				'''
		else:
			bash('oscsend 127.0.0.1 4001 /quitpd i 1') #first quit existing patch
			escapedString =''
			for b in self.menuItems[self.index]:
				if b == "'" or b=="!" or b==" " or b=='$' or b=='(': #special bash characters in path names
					escapedString+= '\\'+b
				else:
					escapedString += b
			if x11Forwarding(): #gui on, audiobuf 10, run it on screen instance if it exists
				command = 'screen -S chamble -X stuff "pd -audioindev 5 -audiooutdev 5 -inchannels 2 -outchannels 2 -blocksize 64 -audiobuf 10 /usr/share/organelle/mother/mother.pd ' \
				+self.userDir + escapedString +'/main.pd  2> /dev/null & \n"'
				a=bash(command)
				time.sleep(.12)
				bash(self.setPid) #put the pid in a file!
				bash(self.chrt) #make sure its RT priority!
				bash(self.taskset) #run it on an reserved CPU!
				self.pid = int(bash('cat /run/patch.pid')[0]) #nicer!
				oled.erase()
				oled.show()
				
			else: #basically -nogui and -audiobuf 6
				bash('/usr/share/organelle/scripts/resetScreen.sh') #just reset the fucking thing
				command = 'screen -S chamble -X stuff "pd -nogui -audioindev 5 -audiooutdev 5 -inchannels 2 -outchannels 2 -blocksize 64 -audiobuf 6 -r 44100 '+ \
				self.Mother + ' ' + self.userDir + str(escapedString) + '/main.pd 2> /dev/null & \n"'
				a=bash(command)
				time.sleep(.12)
				bash(self.setPid) #put the pid in a file!
				bash(self.chrt) #make sure its RT priority!
				bash(self.taskset) #run it on an reserved CPU!

def stopPD():
	bash('kill -9 `cat /run/patch.pid`')
	if x11Forwarding():
		bash('screen -S chamble -X stuff "echo killed\n"')


menuList = MenuItem()

def enc(addr, tags, data, source):
	global pixel
	global graphics
	#bash('setfont usr/share/organelle/configs/LatArCyrHeb-19.psfu.gz')
	#curses.panel.update_panels()
	if pixel == 1:
		bash('setfont usr/share/organelle/configs/LatArCyrHeb-19.psfu.gz')
		pixel = 0
		#curses.endwin()
		#stdscr = curses.initscr()
		#menu = panelGen('menu', stdscr) 
		#curses.reset_prog_mode()
		
	#	graphics.erase()
		#curses.resize_term(14,41)
		#del graphics.window()
		#graphics.delete()
		#graphics.changeFont()
		#menu.changeFont()
		#stardate today: bomble smooched my noggin
		#i felt ok with the world
	#	bash('setfont usr/share/organelle/configs/LatArCyrHeb-19.psfu.gz')
		#graphics.killWindow()
		#curses.resetty()
		
	#	menu.update()
	#	menu.show()
	#	pixel = 0
	'''need patch screen override
	and aux screen override global'''
	global encoderEvent
	encoderEvent =  time.time() 
	if auxsub == 1:
		sendOSCAux("/encoder/turn", direction) #either 0 or 1
		return
	if patchsub == 1:
		sendOSCPD("/encoder/turn", direction)
		return
	if data[0] is 1:
		menu.erase()
		menuList.moveUp()
		tricks = menuList.returnScreen()
		for y,d in enumerate(tricks): #y is index, d is entry
			menu.delete(menu.columns, y,0)
			if menuList.activeEntry() == d:
				menu.string(d,y,0 ,0  )
			else:
				menu.string(d,y,0)
		menu.update()
		menu.show()
	else:
		menu.erase()
		menuList.moveDown()
		tricks = menuList.returnScreen()
		for y,d in enumerate(tricks): #y is index, d is entry
			menu.delete(menu.columns, y,0)
			if menuList.activeEntry() == d:
				menu.string(d,y,0 ,0,  )
			else:
				menu.string(d,y,0)
		menu.update()
		menu.show()


def quitPD(addr, tags, data, source):
	bash('oscsend 127.0.0.1 4001 /quitpd i 1')

def encButton(addr, tags, data, source):
	'''need patch screen override
	and aux screen override global
	
	in menu screen, execute item
	in patch screen, bounce back to menu, unless override is on
	in aux screen, same as patch
	
	'''
	global buttonPressed
	global encoderEvent
	global patchRunning
	if auxsub == 1: #need to do these first
		sendOSCAux("/encoder/button", 1)
		return
	if patchsub == 1:
		sendOSCPD("/encoder/button", 1)
		return
	if data[0] == 1:
		buttonPressed = time.time()
		encoderEvent = time.time() - 6 #just let it take over the patch immediately
		if patchRunning == 1:
			try:
				quitPD()
			except:
				pass
		patchRunning = 1
		time.sleep(.12) #time for patch to close
		menuList.execute() #needs to be better than this
		
	if data[0] == 0:
		if (time.time() - buttonPressed) >= 5.0:
			menu.erase()
			for y in range(11):
				menu.string('SHUTTING DOWN',y,0)
			menu.update()
			menu.show()
			bash('halt') #will this work?




#serial can be sent: /hello, /enablemux, disablemux, /getknobs,  /led

#pd server needs to listen to: /oled/line/X, /oled, /led
#pd needs to be sent: /key, /knobs, /quitpd, 

#server stuff below
serialListener = OSC.ThreadingOSCServer( receiveSer )
pdListener  = OSC.ThreadingOSCServer( receivePD )

#serial listener needs to listen to: /key, /knobs, /enc, /encbut, /hello
serialListener.addMsgHandler("/key", keys) #forward key messages to pd
serialListener.addMsgHandler("/knobs", knobs) #forward knob messages to pd
###############################################################################
serialListener.addMsgHandler("/enc", enc)
serialListener.addMsgHandler("/encbut", encButton) 
###############################################################################
pdListener.addMsgHandler("/enableauxsub",enableAuxSub)			#forwarding encoder movement
pdListener.addMsgHandler("/enablepatchsub", enablePatchSub)		#forwarding ecnoder movement


pdListener.addMsgHandler("/led", led) # handles LED pd -> stm32
for x in range(1,11):
	pdListener.addMsgHandler("/oled/line/"+str(x), screenLine)
	pdListener.addMsgHandler("/oled/aux/"+str(x), auxLine)
pdListener.addMsgHandler("/oled/vumeter", vuMeter) #draws vu meter on line 0
pdListener.addMsgHandler("/erase", erase) #clears screen
pdListener.addMsgHandler("/shutdown",shutdown) #hopefully turns it off
pdListener.addMsgHandler("/oled/setscreen", setScreen) #updates aux screen in system scripts
pdListener.addMsgHandler("/oled/aux/erase",eraseAux) #erase the screen pleaes

pdListener.addMsgHandler("/oled/gSetPixel",pixel)
pdListener.addMsgHandler("/oled/gClear",setPixelScreen) 
pdListener.addMsgHandler("/oled/gLine",graphicsLine) 
pdListener.addMsgHandler("/oled/gCircle",graphicsCircle) 
pdListener.addMsgHandler("/oled/gBox",graphicsBox) 
pdListener.addMsgHandler("/oled/gFillArea",graphicsFill) 
pdListener.addMsgHandler("/oled/gWaveform",graphicsWave) 
pdListener.addMsgHandler("/oled/gFlip",graphicsUpdate) 
#graphicsWave

pdListener.addMsgHandler("/oled/invertline", invertline)
def doNothing(a,t,d,s):
	return

pdListener.addMsgHandler("oled/gInvertArea", doNothing)
SOSC = threading.Thread( target = serialListener.serve_forever )
POSC = threading.Thread( target = pdListener.serve_forever )

SOSC.daemon = True
POSC.daemon = True #they gracefully shutdown on close with this i think
SOSC.start()
POSC.start() 



curses.curs_set(0) #removes blinking cursor
curses.noecho()
curses.start_color()
curses.use_default_colors()
for i in range(0, 8):
	curses.init_pair(i, i, curses.COLOR_BLACK)
	curses.init_pair(i+8, i, curses.COLOR_WHITE)
	curses.init_pair(i+16, i, curses.COLOR_RED)
	curses.init_pair(i+24, i, curses.COLOR_GREEN)
	curses.init_pair(i+32, i, curses.COLOR_YELLOW)
	curses.init_pair(i+40, i, curses.COLOR_CYAN)
	curses.init_pair(i+48, i, curses.COLOR_MAGENTA)
	curses.init_pair(i+56, i, curses.COLOR_BLUE)
stdscr.bkgd(' ', curses.A_BOLD | curses.color_pair(0) ) #black space background
time.sleep(.9)
enc(0,0,'0',0) #so main screen shows
enc(0,0,'1',0)

while True:
	bash('''if [ ! $(pgrep pd | grep $(cat /run/comport.pid)) ]; then pd -nogui -noaudio /usr/share/organelle/comporthandler/papa2.pd 2>/dev/null & echo $! > /run/comport.pid ;fi''') #make sure comport is up!!
	time.sleep(1)

