""" Raytheon - A program to emulate a Raytheon 703 computer """




import pygame, sys, time , random , math , serial
from pygame.locals import *

DEBUG = False           # Control debug prints


# set up pygame
pygame.init()

# Global window definitions


WINDOWWIDTH = 1200

WINDOWHEIGHT = 700 # Total Height of the Window
CONTROLSHEIGHT = WINDOWHEIGHT/2  # Height of the control panel

CORELEFT = WINDOWWIDTH-100
CORETOP = CONTROLSHEIGHT + 4
CORERIGHT = WINDOWWIDTH
COREHEIGHT = 100




# set up the colors as global constants
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255 ,255, 0)
WHITE =(255,255,255)
LIGHTGRAY = (225,225,225)
DARKGRAY = (64, 64, 64)
SCALECOLOR = (128,128,128)


# Set up the contols window global object
windowSurface = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT), 0, 32)
pygame.display.set_caption('Raytheon 703')

#------------------------------------------------------------------
# These are the global registers for the machine
#------------------------------------------------------------------
PCR = 0x0000  # Program counter register
ACR = 0x0000  # Accumulator register
IXR = 0x0000  # Index register
MBR = 0       # Memory buffer register
MAR = 0       # Memory address register
INR = 0       # Instruction register
MSR = 0       # Machine status register
ADFNEG = 0x0400 # negative comparison bit in MSR
ADFEQL = 0x0200 # equal comparison bit in MSR
ADFOVF = 0x0100 # overflow bit
CCFGLB = 0x0080 # global mode bit
HALT = True   # Halt flag
MAXMEMORY = 32768
MEMORY = []
for i in range(MAXMEMORY):
  MEMORY.append(0x0000)
               
#------------------------------------------------------------------
# Implement the ALU (Arithmetic Logical Unit or CPU)
#------------------------------------------------------------------



#------------
# Some private methods to support instructions
#------------

# Compute the effective word address
########################## needs exr and ixr addition ########################

def alu_wordaddress():   
  global PCR,IXR,INR,MSR
  address=INR & 0x07FF  # start with the address from instruction
  if ( (INR & 0x0800) != 0):   # check for index bit
    address = address + (IXR & 0x7FFF)  ## NEED LOCAL/GLOBAL LOGIC HERE
  return address

# Compute the effective byte address
########################## needs exr and ixr addition ########################

def alu_byteaddress():   
  global PCR,ACR,IXR,MBR,MAR,INR,MSR
  address=INR & 0x07FF  # start with the address from instruction
  if ( (address & 0x0001) > 0):
    odd = True
  else:
    odd = False
  return address, odd

# Get a byte from (word) memory based on a byte address in the MAR
# The machine is big endian with most significant byte being the even address
def alu_getbyte():
  global MAR,MBR,MEMORY
  MAR,odd = alu_byteaddress()
  MBR = MEMORY[MAR >>  1] # get the memory word containing the byte
  if (odd):     # Get right byte if odd
    byte = MBR & 0x00FF
  else:
    byte = (MBR & 0xFF00) >> 8     # even get high order byte

  return byte

# Put a byte into a word in memory based on a byte address in the MAR
# The machine is big endian with most significant byte being the even address
def alu_putbyte(byte):
  global ACR,MAR,MBR,MEMORY
  MAR,odd = alu_byteaddress()
  MBR = MEMORY[MAR >> 1] # get the word from memory
  print ('MAR,odd,MBR',MAR,odd,MBR)
  if (odd):   # Put in low order byte if odd
    MBR = (MBR & 0xFF00) |  ( (ACR & 0x00FF))
  else:   # even, put in high order byte
    MBR = (MBR & 0x00FF) | ( (ACR & 0x00FF) << 8)
  MEMORY[(MAR >> 1) & 0x7FFF] = MBR

  return


# set extension register based on PCR (done for all memory reference instructions
############## need logic here ##################
def alu_setexr():
  return

# extend the sign of a 16 bit value to python standard
def alu_extendwordsign(value):
  if  ( (value & 0x8000) == 0): # if positive nothing needed
    return value
  else:
    value =    -( (value & 0x7FFF) ^ 0x7FFF ) - 1
    return value

# extend the sign of a 8 bit value to python standard
def alu_extendbytesign(value):
  if  ( (value & 0x80) == 0): # if positive nothing needed
    return value
  else:
    value =    -( (value & 0x7F) ^ 0x7F ) - 1
    return value


# check for overflow, check sign extended result for an overflow and set overflow
# bit in the machine status word based on the result
################ need logic here #####################
def checkoverflow(value):
  return

def JMP():

  global PCR,MAR
  MAR = alu_wordaddress()
  PCR = MAR
  alu_setexr()   # set extension register
  return

def JSX():        # jump and store return in index (call)
  global IXR,MAR,PCR,MSR,CCFGLB
  MAR = alu_wordaddress()
  IXR = PCR     # PCR has already been incremented
  PCR = MAR
  MSR = MSR | CCFGLB  # force global mode
  alu_setexr()    # set extension register
  return

def STB():        # store byte instruction
  global ACR
  alu_putbyte(ACR & 0x00FF)
  alu_setexr()
  return

def CMB():        # compare byte instruction
  global ACR,MEMORY,MSR,ADFNEG,ADFEQL
  MSR = MSR & (ADFNEG ^ 0XFFFF)   # clear negative flip flop
  MSR = MSR & (ADFEQL ^ 0XFFFF)   # clear equal flip flop
  memvalue = alu_extendbytesign(alu_getbyte())
  acrvalue = alu_extendbytesign(ACR & 0x00FF)
  if (acrvalue == memvalue):
    MSR = MSR | ADFEQL        # compare equal
  if (acrvalue < memvalue):
    MSR = MSR | ADFNEG        # compare less than
  
  alu_setexr()
  return

def LDB():  ## load byte instruction
  global ACR
  byte = alu_getbyte()     # get byte based on address
  ACR = (ACR & 0xFF00) | byte # mask into low order ACR
  alu_setexr()
  return

def STX():
  MAR = alu_wordaddress()
  MEMORY[MAR] = IXR
  alu_setexr()
  return

def STW():
  global ACR,MAR,MEMORY
  MAR = alu_wordaddress()
  MEMORY[MAR] = ACR
  alu_setexr()
  return

def LDW():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY    
  MAR = alu_wordaddress()
  ACR = MEMORY[MAR]
  alu_setexr
  return

def LDX():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY    
  MAR = alu_wordaddress()
  IXR = MEMORY[MAR]
  alu_setexr
  return

def ADD():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY
  MAR = alu_wordaddress()
  value = MEMORY[MAR]
  value = alu_extendwordsign(ACR) + alu_extendwordsign(value) # do the add with extended signs
  checkoverflow(value)  # check for overflow
  ACR = value & 0xFFFF       # trim result to 16 bits
  alu_setexr()
  return

def SUB():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY
  MAR = alu_wordaddress()
  value = MEMORY[MAR]
  value = alu_extendwordsign(ACR) - alu_extendwordsign(value) # do the sub with extended signs
  checkoverflow(value)  # check for overflow
  ACR = value & 0xFFFF       # trim result to 16 bits
  alu_setexr()
  return

def ORI():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY
  MAR = alu_wordaddress()
  ACR = MEMORY[MAR] | ACR
  alu_setexr()
  return

def ORE():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY
  MAR = alu_wordaddress()
  ACR = MEMORY[MAR] ^ ACR
  alu_setexr()
  return

def AND():
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,MEMORY
  MAR = alu_wordaddress()
  ACR = MEMORY[MAR] & ACR
  alu_setexr()
  return

def CMW():
  global ACR,MEMORY,MSR,ADFNEG,ADFEQL
  MAR = alu_wordaddress()
  MSR = MSR & (ADFNEG ^ 0XFFFF)   # clear negative flip flop
  MSR = MSR & (ADFEQL ^ 0XFFFF)   # clear equal flip flop
  memvalue = alu_extendwordsign(MEMORY[MAR])
  acrvalue = alu_extendwordsign(ACR)
  if (acrvalue == memvalue):
    MSR = MSR | ADFEQL        # compare equal
  if (acrvalue < memvalue):
    MSR = MSR | ADFNEG        # compare less than
  
  alu_setexr()
  return

## Instructions decoded with 00 in the high order byte

def HLT():                     # halt instruction
  global HALT
  HALT = True
  return

def INR_():                    # interrupt return
  print('Stub for INR')
  return

def ENB():                    # enable interrupts
  print('Stub for ENB')
  return

def DSB():                    # disable interrupts
  print('Stub for DSB')
  return

def SLM():                    # select local mode
  global MSR,CCFGLB
  MSR = MSR & ~CCFGLB     # clear global bit
  return

def SGM():                    # select global mode
  global MSR,CCFGLB
  MSR = MSR | CCFGLB      # set global bit
  return

def CEX():                    # copy extension to index
  print('Stub for CEX')
  return

def CXE():                    # copy index to extension
  print('Stub for CXE')
  return

def SML():                    # select memory lower
  print('Stub for SML')
  return

def SMU():                    # select memory upper
  print('Stub for SMU')
  return

def MSK():                    # mask interrupts
  print('Stub for MSK')
  return

def UNM():                    # unmask interrupts
  print('Stub for UNM')
  return

##  Instructions decoded with 01 in the upper byte

def CLR():                    # clear accumulator
  global ACR
  ACR = 0       
  return

def CMP():                    # complement accumulator
  global ACR
  ACR = -alu_extendwordsign(ACR) & 0xFFFF
  return

def INV():                    # invert accumulator
  global ACR
  ACR = ACR ^ 0xFFFF
  return

def CAX():                    # copy accumulator to index
  global ACR, IXR
  IXR = ACR
  return

def CXA():                    # copy index to accumulator
  global ACR, IXR
  ACR = IXR
  return

## Instructions with 08 in the upper byte
def SAZ():                    # skip accumulator zero
  global ACR,PCR
  if (ACR == 0): PCR += 1
  return

def SAP():                    # skip accumulator positive
  global ACR,PCR
  if ( (ACR & 0x8000) == 0): PCR += 1
  return

def SAM():                    # skip accumulator minus
  global ACR,PCR
  if ( (ACR & 0x8000) != 0): PCR += 1
  return

def SAO():                    # skip accumulator odd
  global ACR,PCR
  if ( (ACR & 0x0001) != 0): PCR += 1
  return

def SLS():                    # skip accumulator less
  global PCR,MSR,ADFNEG
  if ( (MSR & ADFNEG) != 0): PCR += 1
  return

def SXE():                    # skip index even
  global IXR,PCR
  if ( (IXR & 0x0001) == 0): PCR += 1
  return

def SEQ():                    # skip on compare equal
  global PCR,MSR,ADFEQL
  if ( (MSR & ADFEQL) != 0): PCR += 1
  return

def SNE():                    # skip on compare not equal
  global PCR,MSR,ADFEQL
  if ( (MSR & ADFEQL) == 0): PCR += 1
  return

def SGR():                    # skip on compare greater
  global PCR,MSR,ADFEQL,ADFNEG
  if ( (MSR & (ADFEQL | ADFNEG) ) == 0): PCR += 1
  return

def SLE():                    # skip on compare less than or equal
  global PCR,MSR,ADFEQL,ADFNEG
  if ( (MSR & (ADFEQL | ADFNEG) ) != 0): PCR += 1
  return

def SNO():                    # skip no overflow
  global PCR,MSR,ADFOVF
  if ( (MSR & ADFOVF) == 0): PCR += 1
  return

def SSE():                    # skip on sense switch external false 
  print('Stub for SSE')
  INVALID()
  return

def SS0():                    # skip on sense switch zero false
  global cont,PCR
  if (not cont.SENSELEDS[0].state ): PCR += 1
  return

def SS1():                    # skip on sense switch one false
  global cont,PCR
  if (not cont.SENSELEDS[1].state ): PCR += 1
  return

def SS2():                    # skip on sense switch two false
  global cont,PCR
  if (not cont.SENSELEDS[2].state ): PCR += 1
  return

def SS3():                    #  skip on sense swich three false
  global cont,PCR
  if (not cont.SENSELEDS[3].state ): PCR += 1
  return

## instructions with 09 in the upper byte

def SRA():                    # shift right arithmetic
  global ACR,PCR
  count = INR & 0x000F    # isolate shift count
  ACR = (alu_extendwordsign(ACR) >> count) & 0xFFFF
  return

def SLA():                    # shift left arithmetic
  print('Stub for SLA')
  return

def SRAD():                   # shift right arithmetic double
  print('Stub for SRAD')
  return

def SLAD():                   # shift left arithmetic double
  print('Stub for SLAD')
  return

## instructions with 0A in the upper byte

def SRL():                                        # shift right logical
  global ACR,INR
  count = INR & 0x000F        # isolate shift count
  ACR = ( (ACR >> count) & 0xFFFF)
  return

def SLL():                                         # shift left logical
  global ACR,INR
  count = INR & 0x000F        # isolate shift count
  ACR = ( (ACR << count) & 0xFFFF)
  return

def SRLD():                                       # shift right logical double 
  global ACR,IXR,INR
  count = INR & 0x000F    # isolate shift count
  while (count > 0):
    carry = ACR & 0x0001  # remember LSB
    ACR = ( (ACR >> 1) & 0x7FFF)
    IXR = ( (IXR >> 1) & 0x7FFF)    
    if (carry > 0):
      IXR = IXR | 0x8000  # shift ACR LSB to IXR MSB
    count -= 1
  return

def SLLD():                                       # shift left logical double
  global ACR,IXR,INR
  count = INR & 0x000F    # isolate shift count
  while (count > 0):
    carry = IXR & 0x8000  # remember MSB of IXR
    ACR = ( (ACR << 1) & 0xFFFE)
    IXR = ( (IXR << 1) & 0xFFFE)    
    if (carry > 0):
      ACR = ACR | 0x0001  # shift IXR MSB to ACR LSB
    count -= 1
  return

def SRC():                                          # shift right circular
  global ACR,INR
  count = INR & 0x000F    # isolate shift count
  while (count > 0):
    carry = ACR & 0x0001  # remember LSB
    ACR = ( (ACR >> 1) & 0x7FFF)
    if (carry > 0):
      ACR = ACR | 0x8000  # circle round the LSB
    count -= 1
  return

def SLC():                                          # shift left circular
  global ACR,INR
  count = INR & 0x000F    # isolate shift count
  while (count > 0):
    carry = ACR & 0x8000  # remember MSB
    ACR = ( (ACR << 1) & 0xFFFE)
    if (carry > 0):
      ACR = ACR | 0x0001  # circle round the MSB
    count -= 1
  return

def SRCD():                   # shift right circular double
  print('Stub for SRCD')
  return

def SLCD():                   # shift left circular double
  print('Stub for SLCD')
  return

def SRLL():                   # shift right logical right byte
  print('Stub for SRLL')
  return

def SLLL():                   # shift left logical left byte
  print('Stub for SLLL')
  return

def SRLR():                   # shift right logical right byte 
  print('Stub for SRLR')
  return

def SLLR():                   # shift left logical right byte
  print('Stub for SLLR')
  return

def SRCL():                   # shift right circular left byte
  print('Stub for SRCL')
  return

def SLCL():                   # shift left circular left byte
  print('Stub for SLCL')
  return

def SRCR():                   # shift right circular right byte
  print('Stub for SRCR')
  return

def SLCR():                   # shift left circular right byte
  print('Stub for SLCR')
  return

## misc instructions

def DIN():                    # direct input
  print('Stub for DIN')
  return

def DOT():                    # direct output 
  print('Stub for DOT')
  return

def IXS():                    # increment index and skip greater or equal zero
  global IXR,PCR,INR
  IXR = alu_extendwordsign(IXR) + (INR & 0x00FF)      # increment index
  if (IXR >= 0): PCR += 1
  IXR = IXR & 0xFFFF      # restore to 16 bits
  return

def DXS():                    # decrement index and skip less than zero
  global IXR,PCR,INR
  IXR = alu_extendwordsign(IXR) - (INR & 0x00FF)      # increment index
  if (alu_extendwordsign(IXR) < 0): PCR += 1
  IXR = IXR & 0xFFFF      # restore to 16 bits
  return

def LLB():                    # load literal byte
  global ACR,INR
  ACR = (ACR & 0xFF00) | (INR & 0x00FF)
  return

def CLB():                    # compare literal byte
  print('Stub for CLB')
  return


def INVALID():                # invalid instruction
  global HALT,INR,PCR
  print ('Invalid instruction INR%4X at PCR%4X' %(INR,PCR-1) )
  HALT = True
  return

#------------
# Instruction execution decoder
#------------
memref_inst = {0x1000:JMP, 0x2000: JSX, 0x3000:STB, 0x4000:CMB,
          0x5000:LDB, 0x6000:STX, 0x7000:STW, 0x8000:LDW,
          0x9000:LDX, 0xA000:ADD, 0xB000:SUB, 0xC000:ORI,
          0xD000:ORE, 0xE000:AND, 0xF000:CMW}

control_inst = {0x0000:HLT, 0x0010:INR_, 0x0020:ENB, 0x0030:DSB,
                0x0040:SLM, 0x0050:SGM,  0x0060:CEX, 0x0070:CXE,
                0x0080:SML, 0x0090:SMU,  0x00A0:MSK, 0x00B0:UNM}

register_inst = {0x0100:CLR, 0x0110:CMP, 0x0120:INV, 0x0130:CAX,
                 0x0140:CXA}

skip_inst = {0x0800:SAZ, 0x0810:SAP, 0x0820:SAM, 0x0830:SAO,
             0x0840:SLS, 0x0850:SXE, 0x0860:SEQ, 0x0870:SNE,
             0x0880:SGR, 0x0890:SLE, 0x08A0:SNO, 0x08B0:SSE,
             0x08C0:SS0, 0x08D0:SS1, 0x08E0:SS2, 0x08F0:SS3}

shifta_inst = {0x0900:SRA, 0x0910:SLA, 0x0920:SRAD, 0x0930:SLAD}

shiftl_inst = {0x0A00:SRL,  0x0A10:SLL,  0x0A20:SRLD, 0x0A30:SLLD,
               0x0A40:SRC,  0x0A50:SLC,  0x0A60:SRCD, 0x0A70:SLCD,
               0x0A80:SRLL, 0x0A90:SLLL, 0x0AA0:SRLR, 0x0AB0:SLLR,
               0x0AC0:SRCL, 0x0AD0:SLCL, 0x0AE0:SRCR, 0x0AF0:SLCR}

misc_inst =   {0x0200:DIN, 0x0300:DOT, 0x0400:IXS, 0x0500:DXS,
               0x0600:LLB, 0x0700:CLB}


def alu_execute(numsteps):
  global PCR,ACR,IXR,MBR,MAR,INR,MSR,HALT
# this is the entry point to execute one or more instructions
# the number to execute (unless a halt is encountered) is numsteps

  HALT = False
  while ( numsteps > 0 ):
    numsteps -= 1    
    # begin execution by fetching the next instruction per the PCR and increment PCR

    MBR=MEMORY[PCR]     # load memory buffer
    INR = MBR           # also the instruction register



    PCR += 1  # increment the PCR for all but halt

    opcode1 = INR & 0xF000
    opcode2 = INR & 0xFF00
    opcode3 = INR & 0xFFF0



    if (opcode1 != 0):    # decode memory reference instructions
      inst = memref_inst.get(opcode1,INVALID)  # look up the function
      inst()        # execute the function for the instruction


    elif (opcode2 == 0):    # handle instructions with 00 in high order byte
      inst = control_inst.get(opcode3,INVALID)  # look up the function
      inst()        # execute the function for the instruction


    elif (opcode2 == 0x0100):    # handle instructions with 01 in high order byte
      inst = register_inst.get(opcode3,INVALID)  # look up the function
      inst()        # execute the function for the instruction
      
 
    elif (opcode2 == 0x0800):    # handle instructions with 08 in high order byte
      inst = skip_inst.get(opcode3,INVALID)  # look up the function
      inst()        # execute the function for the instruction
      
    elif (opcode2 == 0x0900):    # handle instructions with 09 in high order byte
      inst = shifta_inst.get(opcode3,INVALID)  # look up the function
      inst()        # execute the function for the instruction
      

    elif (opcode2 == 0x0A00):    # handle instructions with 0A in high order byte
      inst = shiftl_inst.get(opcode3,INVALID)  # look up the function
      inst()        # execute the function for the instruction
      
    # decode misc instructions not caught above
 
    else:
      inst = misc_inst.get(opcode2,INVALID)   # look up function
      inst()        # execute the function for the instruction

     
    if(HALT): return HALT    # exit if we encounted halt or invalid instruction
    continue

 
  return HALT     # ran the requested number of instructions


#------------------------------------------------------------------
# Define the widget classes
#------------------------------------------------------------------

class Widget(object):
# Widget class for all widgets,  its  function is mainly to hold the
# dictionary of all widget objects by name as well as the application
# specific handler function. And support isclicked to
# see if cursor is clicked over widget.

    widgetlist = {} # dictionary of tubles of (button_object,app_handler)
    background_color = LIGHTGRAY

    def __init__(self):
    # set up default dimensions in case they are not defined in
    # inherited class, this causes isclicked to default to False
        self.left = -1
        self.width = -1
        self.top = -1
        self.height = -1

    def find_widget(widget_name):
    # find the object handle for a widget by name        
        if widget_name in Widget.widgetlist:
            widget_object = Widget.widgetlist[widget_name][0]
            return  widget_object
        else:
            Print ('Error in find_widget, Widget not found ' + widget_name)
            return

    def isclicked (self, curpos):
    # button was clicked, is this the one? curpos is position tuple (x,y)
        

        covered = False

        if (curpos[0] >= self.left and
        curpos[0] <= self.left+self.width and
        curpos[1] >= self.top and
        curpos[1] <= self.top + self.height):
            covered = True

        return covered
    

    def handler(self):
    # prototype for a widget handler to be overridden if desired
        pass     
            
class Button(Widget):

    buttonlist = []
    grouplist = {}
    
    def __init__ (self, window = windowSurface,color = BLACK,
                  topleft = (200,200), size=20,name = '', label='',
                  value = '',app_handler=Widget.handler,
                  group = '',groupaction = 'RADIO'):   

        self.window = window
        self.color = color
        self.topleft = topleft
        self.left = topleft[0]  # required by isclicked method in Widget
        self.top = topleft[1]   # "
        self.width = size       # "
        self.height = size      # "
        self.right = self.left + size
        self.bottom = self.top + size
        self.size = size
        self.name = name
        self.label = label
        self.value = value
        self.app_handler = app_handler # object of applications specific handler
        self.group = group
        
        self.groupaction = groupaction
        # groupaction value of 'RADIO' allows only one in group to be on
        # 'RADIO_WITH_OFF' allows only one but all off also
        # '' means no group action required

        self.state = False    # Initialize button state to 'off'


        # Add widget object keyed by name to widget dictionary.
        # Non-null Widget names must be unique.
        
        if ( (name != '') and (name not in Widget.widgetlist) ):
            Widget.widgetlist[name] = (self,app_handler)
        else:
            print ('Error - duplicate widget name of ' + name)

        Button.buttonlist += [self] # add to button list as a object

        # if button is in a group, add group to dictionary if the group is not
        # already there.  Then add the button to the group.

        if group in Button.grouplist:
            Button.grouplist[group] += (self,)
        else:
            Button.grouplist[group] = (self,)


        
        # get the rectangle for the object
        self.rect = pygame.draw.rect(window,color,
        (topleft[0],topleft[1],size,size),1)

        #write label if any
        if label != '':
           self._label()
            
        self.draw()

    def _label(self): # private method to generate label, does not do draw
       labelFont = pygame.font.SysFont(None, int(self.size*1.5) )
       text = labelFont.render(self.label,True,self.color,
       Widget.background_color)
       
       textRect= text.get_rect()
       textRect.left = self.rect.right + 5
       textRect.bottom = self.rect.bottom
       self.window.blit(text, textRect)
                                                   

    def identify(self):  # print my name
        print ("Button name is:" + self.name)

    def draw (self): # draw button with current state
        
        self.rect = pygame.draw.rect(self.window, self.color,
        self.rect,1)

        if self.state:

            pygame.draw.circle(self.window,self.color,
            (self.rect.left+int(self.size/2),self.rect.top+int(self.size/2))
            ,int(self.size/2)-2,0)
        else:
            pygame.draw.circle(self.window,WHITE,
            (self.rect.left+int(self.size/2),self.rect.top+int(self.size/2)),
            int(self.size/2)-2,0)
            
            pygame.draw.circle(self.window,self.color,
            (self.rect.left+int(self.size/2),self.rect.top+int(self.size/2)),
            int(self.size/2)-2,1)
                               
        pygame.display.update()   # refresh the screen

    def toggle (self):  # toggle the button state
        if self.state:
            self.state = False
        else:
            self.state = True
            
        self.draw()



    def group_handler(self):
    # if button in a group, button is now on and is a RADIO button  then
    # turn off all other buttons in the group

        #if groupaction is 'RADIO' or 'RADIO_WITH_OFF'and new state is on,
        # turn off all other buttons in the group. 
        if ( (self.groupaction == 'RADIO') |
             (self.groupaction == 'RADIO_WITH_OFF') ):

            # loop finding other buttons in group and turning them off
            for i in range(len((Button.buttonlist))):

                if (Button.buttonlist[i].group == self.group and
                Button.buttonlist[i] != self):
                    Button.buttonlist[i].state = False
                    Button.draw(Button.buttonlist[i])

        # Now, if 'RADIO' and if new state is off,
        # tun it back on because at least one must be on in the group.
        if self.groupaction == 'RADIO':
            if (self.state == False):
                self.toggle()
                return
#------------------------------------------------------------
# Button handler method,  overriding the Widget
# handler method prototype. Does some general work then calls the
# group handler and application specific handler if any
#------------------------------------------------------------

    def handler(self):


        # toggle the state of the button
        self.toggle()

        # see if button is in a group and if so, call  the group handler
        # in button class to enforce such things as 'RADIO' exclusivity
        if self.group != '':
            self.group_handler()

        # call the application specific handler (if none specified when
        # button is created it defaults to dummy prototype Widget.handler).
        self.app_handler(self)







            
        return

    



class Led(Widget):
# Inherit Widget class to implement and LED light. A circle showing
# states associated with OFF and ON

    def __init__ (self, window = windowSurface,
                  color = BLACK, # this is outline color for off state
                  topleft = (750,256), size=20,name = '',
                  label='',app_handler=Widget.handler,
                  state = 'OFF',offcolor=BLACK,oncolor=RED,value=0x0000):
   

        self.window = window
        self.color = color
        self.topleft = topleft
        self.left = topleft[0]
        self.top = topleft[1]
        self.right = self.left + size
        self.bottom = self.top + size
        self.center = ( self.left + int( size/2) , self.top + int (size/2) )
        self.size = size
        self.width = size
        self.height = size
        self.name = name
        self.label = label
        self.app_handler = app_handler
        self.state = state
        self.offcolor = offcolor
        self.oncolor = oncolor
        self.value = value


        # Add widget object keyed by name to widget dictionary. Widget names
        # must be unique.
        
        if name in Widget.widgetlist:
            print ('Error - duplicate widget name of ' + name)
        else:
            Widget.widgetlist[name] = (self,app_handler)


        #write label if any
        if label != '':
           self._label()
            
        self.draw()

    def _label(self): # private method to generate label, does not do update
       labelFont = pygame.font.SysFont(None, int(self.size) )
       text = labelFont.render(self.label,True,self.color,
       Controls.background_color)
       
       textRect= text.get_rect()
       textRect.left = self.right + 5
       textRect.bottom = self.bottom
       self.window.blit(text, textRect)
                                                   

    def identify(self):  # print my name
        print ("Button name is:" + self.name)


    def toggle(self):  # toggle the LED state
        
        if self.state == 'OFF':
            self.state = 'ON'
        elif self.state == 'ON':
            self.state = 'OFF'
        else :
            print('Invalid LED state = ' + self.state)
            self.state = 'OFF'

        self.draw()

    def draw (self): # draw LED with current state
        
        if self.state == 'OFF':
            colortuple = self.offcolor
        elif self.state == 'ON':
            colortuple = self.oncolor
        else :
            print('Invalid LED state = ' + self.state)
            colortuple = self.offcolor
    
        pygame.draw.circle(self.window,colortuple,
            (self.left+int(self.size/2),self.top+int(self.size/2))
            ,int(self.size/2)-2,0)

        pygame.display.update()   # refresh the screen

    def handler(self):  # led handler
        self.app_handler(self)  # nothing special to do, call app_handler
        return


class Text(Widget):

    def __init__(self,window=windowSurface,
                 color=BLACK,background_color=Widget.background_color,
                 topleft=(200,200),name= '',
                 font_size=20,max_chars=20,text='',
                 outline=True,outline_width=1,
                 justify = 'LEFT',
                 app_handler=Widget.handler):

        
        # initialize the properties
        self.window=window
        self.color= color
        self.background_color = background_color
        self.name = name
        self.font_size = font_size
        self.max_chars = max_chars
        self.text = text
        self.outline = outline
        self.outline_width = outline_width
        self.justify = justify
        self.app_handler = app_handler
        
        self.topleft=topleft
        self.left=topleft[0]    # reguired by isclicked method in Widget
        self.top=topleft[1]     # "
        
        # render a maximum size string to set size of text rectangle
        max_string = ''
        for i in range(0,max_chars):
            max_string += 'D'

        maxFont = pygame.font.SysFont(None,font_size)
        maxtext = maxFont.render(max_string,True,color)
        maxRect= maxtext.get_rect()
        maxRect.left = self.left
        maxRect.top = self.top
        self.maxRect = maxRect  # save for other references
        self.maxFont = maxFont

        # now set the rest required by isclicked method
        self.width = maxRect.right - maxRect.left
        self.height = maxRect.bottom -  maxRect.top


        # Add widget object keyed by name to widget dictionary.
        # Non-null Widget names must be unique.
        
        if ( (name != '') and (name not in Widget.widgetlist) ):
            Widget.widgetlist[name] = (self,app_handler)
        elif (name != ''):
            print ('Error - duplicate widget name of ' + name)

        self.draw()  # invoke the method to do the draw

        return   # end of Text initializer

    # Text method to draw the text and any outline on to the screen
    def draw(self):
        # fill the maxRect to background color to wipe any prev text
        pygame.draw.rect(self.window,self.background_color,
                         (self.maxRect.left,self.maxRect.top,
                          self.width, self.height),0)

        # if outline is requested, draw the outline 4 pixels bigger than
        # max text.  Reference topleft stays as specified
        
        if self.outline:
            pygame.draw.rect(self.window,self.color,
                             (self.maxRect.left-self.outline_width-2,
                              self.maxRect.top-self.outline_width-2,
                              self.width+(2*self.outline_width)+2,
                              self.height+(2*self.outline_width)+2),
                              self.outline_width)


        # Now put the requested text within maximum rectangle
        plottext = self.maxFont.render(self.text,True,self.color)
        plotRect = plottext.get_rect()

        plotRect.top = self.top # top doesn't move with justify

        # justify the text
        if self.justify == 'CENTER':
            plotRect.left = self.left + int(plotRect.width/2) 
        elif self.justify == 'LEFT':
            plotRect.left = self.left
        elif self.justify == 'RIGHT':
            plotRect.right = self.maxRect.right
        else:
            print('Illegal justification in Text object ',self.justify, end='\n')

        # blit the text and update screen
        self.window.blit(plottext,plotRect)

        pygame.display.update()

    # Text method to update text and redraw
    def update(self,text):
        self.text = text
        self.draw()

class Rectangle(Widget):
# class to wrap the pygame rectangle class to standardize with Widgets 

    def __init__(self, window=windowSurface,color=BLACK,
                 topleft = (200,200), width = 30, height = 20,
                 name = '',outline_width = 1, # width of outline, 0 = fill
                 app_handler=Widget.handler):

        self.window = window
        self.color = color
        self.topleft = topleft
        self.left = topleft[0]      # required by isclicked method in Widget
        self.top = topleft[1]       # "
        self.width = width          # "
        self.height = height        # "
        self.right = self.left + width
        self.bottom = self.top + height
        self.name = name
        self.outline_width = outline_width
        self.app_handler = app_handler

        # Add widget object keyed by name to widget dictionary.
        # Non-null Widget names must be unique.
        
        if ( (name != '') and (name not in Widget.widgetlist) ):
            Widget.widgetlist[name] = (self,app_handler)
        elif (name != ''):
            print ('Error - duplicate widget name of ' + name)

        self.draw()  # invoke the draw method to draw it

        return

    def draw(self):     # Rectangle method to do the draw
        
        # get a rectangle object and draw it
        self.rect = pygame.Rect(self.left,self.top,self.width,self.height)
        pygame.draw.rect(self.window,self.color,self.rect,
                         self.outline_width)
        pygame.display.update(self.rect)

        return
    
    def handler(self):  # Rectangle handler
        self.app_handler(self)  # nothing special to do, call app_handler
        return
    
class Controls(object):
  """ The controls portion of the front panel """

  PCRLEDS = []  # list to hold PCRLED objects
  REGLEDS = []  # list to hold register LED objects
  REGSELS = []  # list to hold register select button objects
  SENSELEDS = []# list to hold the sense button objects
  
  # define the control attributes describing where the controls rectangle
  # is on the front panel
  background_color = Widget.background_color

  right = WINDOWWIDTH
  
  left = 0
  top = 0
  
  def __init__(self,window = windowSurface):  # initializer


    self.window = window  # local object of window surface
    
    # define the controls portion as a rectangle
    self.rect = pygame.Rect(Controls.left, Controls.top,
                                Controls.right, CONTROLSHEIGHT)
    # set up fonts
    self.basicFont = pygame.font.SysFont(None, 15)

  def updatePCRLEDS(self): # update the controls PCR leds with an integer value
    global PCR

    for led in self.PCRLEDS:  # run loop to update leds per the PCR
      if ( (PCR & led.value) == 0):
        led.state = 'OFF'
      else:
        led.state = 'ON'
      led.draw() # redraw this led with state

  def updateREGLEDS(self): # update the register leds depending on which register selected
    # also update the display enter leds to show only valid in MBR selected
    global ACR,IXR,MBR,MAR,INR,MSR

    if (cont.ACRsel.state):
      value = ACR
    elif (cont.IXRsel.state):
      value = IXR
    elif (cont.MBRsel.state):
      value = MBR
    elif (cont.INRsel.state):
      value = INR
    elif (cont.MARsel.state):
      value = MAR
    elif (cont.MSRsel.state):
      value = MSR
    else:
      print ('tilt in updateREGLEDS no select found')

    for led in self.REGLEDS:  # run loop to update leds per the selected register
      if ( (value & led.value) == 0):
        led.state = 'OFF'
      else:
        led.state = 'ON'
      led.draw() # redraw this led with state

    # update the display/enter LED's
    if (cont.MBRsel.state):
      cont.displayLED.state = 'ON'
      cont.enterLED.state='ON'
    else:
      cont.displayLED.state = 'OFF'
      cont.enterLED.state='OFF'      
   
    cont.displayLED.draw()
    cont.enterLED.draw()  

  def draw_controls(self): # draw the controls portion of the computer
    pygame.draw.rect(self.window, self.background_color, self.rect)
    pygame.display.update(self.rect)

class Core(object):
  """ The core memory save/restore portion of the auxilary panel """

  
  # define the control attributes describing where the core save/restore rectangle
  # is on the front panel
  background_color = Widget.background_color

  
  def __init__(self,window = windowSurface):  # initializer


    self.window = window  # local object of window surface
    
    # define the controls portion as a rectangle
    self.rect = pygame.Rect(CORELEFT, CORETOP,
                            CORERIGHT, COREHEIGHT)
    # set up fonts
    self.basicFont = pygame.font.SysFont(None, 15)

    # draw the core panel
    self.draw()

    self.label = Text(name = 'corelabel',topleft=(CORELEFT+20,CORETOP+5),
                      outline=False,text='Core',font_size=35)
    
    self.coresave = Button(name='coresave',color=BLACK,
                    topleft=(CORELEFT+10,CORETOP+40),size = 15,
                    value=0,label='Save',app_handler=coresave_handler,
                    group='Core',groupaction='RADIO')

    self.corerestore = Button(name='corerestore',color=BLACK,
                    topleft=(CORELEFT+10,self.coresave.bottom+10),size = 15,
                    value=0,label='Restore',app_handler=corerestore_handler,
                    group='Core',groupaction='RADIO')  


    
  def draw(self): # draw the core portion of the computer
    pygame.draw.rect(self.window, self.background_color, self.rect)
    pygame.display.update(self.rect)

#----------------------------------------------------------------
# Applications specific handlers called by the widget object handler
# (i.e. Button.handler) after routine actions such as button toggle and
# group handling.
#-------------------------------------------------------------------
def coresave_handler(button_object):
  global MEMORY
  with  open("memory.dat", "w") as memory_file:
    for i in range(MAXMEMORY):
      memory_file.write(hex(MEMORY[i]) )
      memory_file.write('\n')
  button_object.toggle()  # turn off the indicator
  return

def corerestore_handler(button_object):
  global MEMORY
  with open("memory.dat", "r") as memory_file:
    for i in range(MAXMEMORY):
      MEMORY[i] = memory_file.readline()
      MEMORY[i] = MEMORY[i][0:-1]      # remove trailing new line
      MEMORY[i] = int(MEMORY[i],0)  
  button_object.toggle()  # turn off the indicator
  return


# function to handle click on a PCR LED, called with a LED object
def pcrled_handler(pcrled_object):
  global PCR
  PCR = PCR ^ pcrled_object.value  # toggle the appropiate bit
  pcrled_object.draw()

# function to handle click on the clear PCR LED, called with a LED object
def clrpcr_handler(pcrled_object):
  global PCR
  PCR = 0              # zero the PCR
  pcrled_object.draw()

# function to handle click on the selected register LED, called with a LED object
def regled_handler(regled_object):
  global ACR,IXR,MBR
  regled_object.toggle()
  if (cont.ACRsel.state):
    ACR = getregvalue()
  elif (cont.IXRsel.state):
    IXR = getregvalue()
  elif (cont.MBRsel.state):
    MBR = getregvalue() # others can't be updated here

  regled_object.draw()
  
# function to return a value based on the current setting of the register leds
############# put in check to inhibit when running ######################
def getregvalue():
  value = 0  # default to no bits set

  for led in Controls.REGLEDS:  # run loop to update leds per the selected register
    if (led.state == 'ON'):
      value = value | led.value  # set bit coresponding to this led

  return value  

#function to handle click on the clear selected register LED, called with a LED object
def clrreg_handler(regled_object):
  global ACR,IXR,MBR

  if (cont.ACRsel.state):
    ACR = 0
  elif (cont.IXRsel.state):
    IXR = 0
  elif (cont.MBRsel.state):
    MBR = 0 # others can't be updated here

  regled_object.draw()

# function to handle click on the display LED
def displayled_handler(led_object):
  global PCR,MBR,MEMORY

  MBR = MEMORY[PCR]
  PCR += 1            

# function to handle click on the enter LED
def enterled_handler(led_object):
  global PCR,MBR,MEMORY

  MEMORY[PCR] = MBR
  PCR += 1
  return



# function to handle click on the run/halt LED
def runled_handler(led_object):
  led_object.toggle()   # just flip the on/off state
  return


# function to handle click on the step LED
def stepled_handler(led_object):
  led_object.toggle()   # just flip the on/off state
  return

# function to handle click on the clear all LED
def clearled_handler(led_object):
  global PCR,ACR,IXR,MBR,MAR,INR,MSR
  PCR = 0       # clear out all the registers
  ACR = 0
  IXR = 0
  MBR = 0
  MAR = 0
  INR = 0
  MSR = 0
  return  

#------------------------------------------------------------
# Applications specific setup functions not part of a class
#------------------------------------------------------------

def init_controls():

# Function to intialize the controls portion of scope by drawing the
# controls and setting parameters to intitial values.
# Returns a handle to the created controls object.
    
  # create the controls object
  cont = Controls()

  # draw the controls screen
  cont.draw_controls() 

  # Build the PCR display


  cont.clrPCRLED = Led(name='clrPCRLED',color=BLACK,
                topleft = (cont.left+50,cont.top+50),size=30,
                label = '',app_handler=clrpcr_handler,
                state = 'OFF')





  cont.PCRLED14 = Led(name='PCRLED14',color=BLACK,
              topleft = (cont.clrPCRLED.left+200,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x4000)
  Controls.PCRLEDS += [cont.PCRLED14] # add to list of PCRLEDS as a object
  
  cont.PCRLED13 = Led(name='PCRLED13',color=BLACK,
              topleft = (cont.PCRLED14.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x2000)
  Controls.PCRLEDS += [cont.PCRLED13] # add to list of PCRLEDS as a object

  cont.PCRLED12 = Led(name='PCRLED12',color=BLACK,
              topleft = (cont.PCRLED13.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x1000)
  Controls.PCRLEDS += [cont.PCRLED12] # add to list of PCRLEDS as a object
  
  cont.PCRLED11 = Led(name='PCRLED11',color=BLACK,
              topleft = (cont.PCRLED12.left+100,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0800)
  Controls.PCRLEDS += [cont.PCRLED11] # add to list of PCRLEDS as a object
  
  cont.PCRLED10 = Led(name='PCRLED10',color=BLACK,
              topleft = (cont.PCRLED11.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0400)
  Controls.PCRLEDS += [cont.PCRLED10] # add to list of PCRLEDS as a object
  
  cont.PCRLED9 = Led(name='PCRLED9',color=BLACK,
              topleft = (cont.PCRLED10.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0200)
  Controls.PCRLEDS += [cont.PCRLED9] # add to list of PCRLEDS as a object
  
  cont.PCRLED8 = Led(name='PCRLED8',color=BLACK,
              topleft = (cont.PCRLED9.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0100)
  Controls.PCRLEDS += [cont.PCRLED8] # add to list of PCRLEDS as a object
  
  cont.PCRLED7 = Led(name='PCRLED7',color=BLACK,
              topleft = (cont.PCRLED8.left+100,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0080)
  Controls.PCRLEDS += [cont.PCRLED7] # add to list of PCRLEDS as a object
  
  cont.PCRLED6 = Led(name='PCRLED6',color=BLACK,
              topleft = (cont.PCRLED7.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0040)
  Controls.PCRLEDS += [cont.PCRLED6] # add to list of PCRLEDS as a object
  
  cont.PCRLED5 = Led(name='PCRLED5',color=BLACK,
              topleft = (cont.PCRLED6.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0020)
  Controls.PCRLEDS += [cont.PCRLED5] # add to list of PCRLEDS as a object
  
  cont.PCRLED4 = Led(name='PCRLED4',color=BLACK,
              topleft = (cont.PCRLED5.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0010)
  Controls.PCRLEDS += [cont.PCRLED4] # add to list of PCRLEDS as a object
  
  cont.PCRLED3 = Led(name='PCRLED3',color=BLACK,
              topleft = (cont.PCRLED4.left+100,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0008)
  Controls.PCRLEDS += [cont.PCRLED3] # add to list of PCRLEDS as a object
  
  cont.PCRLED2 = Led(name='PCRLED2',color=BLACK,
              topleft = (cont.PCRLED3.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0004)
  Controls.PCRLEDS += [cont.PCRLED2] # add to list of PCRLEDS as a object
  
  cont.PCRLED1 = Led(name='PCRLED1',color=BLACK,
              topleft = (cont.PCRLED2.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0002)
  Controls.PCRLEDS += [cont.PCRLED1] # add to list of PCRLEDS as a object
  
  cont.PCRLED0 = Led(name='PCRLED0',color=BLACK,
              topleft = (cont.PCRLED1.left+50,cont.clrPCRLED.top),size=30,
              label='',app_handler = pcrled_handler,
              state = 'OFF',value=0x0001)
  Controls.PCRLEDS += [cont.PCRLED0] # add to list of PCRLEDS as a object

  # label the PCR
  cont.pcrlabel = Text(topleft = (cont.PCRLED9.left,cont.PCRLED7.bottom+20),
                  font_size=30,outline=False,text = 'PROGRAM COUNTER')

  
# define the register display

  cont.clrREGLED = Led(name='clrREGLED',color=BLACK,
                topleft = (cont.left+50,cont.top+150),size=30,
                label = '',app_handler=clrreg_handler,
                state = 'OFF')


  cont.REGLED15 = Led(name='REGLED15',color=BLACK,
              topleft = (cont.clrREGLED.left+150,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x8000)
  Controls.REGLEDS += [cont.REGLED15] # add to list of REGLEDS as a object
  
  cont.REGLED14 = Led(name='REGLED14',color=BLACK,
              topleft = (cont.REGLED15.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x4000)
  Controls.REGLEDS += [cont.REGLED14] # add to list of REGLEDS as a object
  
  cont.REGLED13 = Led(name='REGLED13',color=BLACK,
              topleft = (cont.REGLED14.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x2000) 
  Controls.REGLEDS += [cont.REGLED13] # add to list of REGLEDS as a object
  
  cont.REGLED12 = Led(name='REGLED12',color=BLACK,
              topleft = (cont.REGLED13.left+50,cont.clrREGLED.top),size=30,  
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x1000)
  Controls.REGLEDS += [cont.REGLED12] # add to list of REGLEDS as a object
  
  cont.REGLED11 = Led(name='REGLED11',color=BLACK,
              topleft = (cont.REGLED12.left+100,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0800)
  Controls.REGLEDS += [cont.REGLED11] # add to list of REGLEDS as a object
  
  cont.REGLED10 = Led(name='REGLED10',color=BLACK,
              topleft = (cont.REGLED11.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0400)
  Controls.REGLEDS += [cont.REGLED10] # add to list of REGLEDS as a object
  
  cont.REGLED9 = Led(name='REGLED9',color=BLACK,
              topleft = (cont.REGLED10.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0200)
  Controls.REGLEDS += [cont.REGLED9] # add to list of REGLEDS as a object
  
  cont.REGLED8 = Led(name='REGLED8',color=BLACK,
              topleft = (cont.REGLED9.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0100)
  Controls.REGLEDS += [cont.REGLED8] # add to list of REGLEDS as a object
  
  cont.REGLED7 = Led(name='REGLED7',color=BLACK,
              topleft = (cont.REGLED8.left+100,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0080)
  Controls.REGLEDS += [cont.REGLED7] # add to list of REGLEDS as a object
  
  cont.REGLED6 = Led(name='REGLED6',color=BLACK,
              topleft = (cont.REGLED7.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0040)
  Controls.REGLEDS += [cont.REGLED6] # add to list of REGLEDS as a object
  
  cont.REGLED5 = Led(name='REGLED5',color=BLACK,
              topleft = (cont.REGLED6.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0020)
  Controls.REGLEDS += [cont.REGLED5] # add to list of REGLEDS as a object
  
  cont.REGLED4 = Led(name='REGLED4',color=BLACK,
              topleft = (cont.REGLED5.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0010)
  Controls.REGLEDS += [cont.REGLED4] # add to list of REGLEDS as a object
  
  cont.REGLED3 = Led(name='REGLED3',color=BLACK,
              topleft = (cont.REGLED4.left+100,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0008)
  Controls.REGLEDS += [cont.REGLED3] # add to list of REGLEDS as a object
  
  cont.REGLED2 = Led(name='REGLED2',color=BLACK,
              topleft = (cont.REGLED3.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0004)
  Controls.REGLEDS += [cont.REGLED2] # add to list of REGLEDS as a object
  
  cont.REGLED1 = Led(name='REGLED1',color=BLACK,
              topleft = (cont.REGLED2.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0002)
  Controls.REGLEDS += [cont.REGLED1] # add to list of REGLEDS as a object
  
  cont.REGLED0 = Led(name='REGLED0',color=BLACK,
              topleft = (cont.REGLED1.left+50,cont.clrREGLED.top),size=30,
              label='',app_handler=regled_handler,
              state = 'OFF',value=0x0001)
  Controls.REGLEDS += [cont.REGLED0] # add to list of REGLEDS as a object

  # label the register display
  cont.reglabel = Text(topleft = (cont.REGLED9.left,cont.REGLED9.bottom+20),
                  font_size=30,outline=False,text = 'SELECTED REGISTER')
  
  ## define the register select buttons (substitute for rotary switch

  cont.ACRsel = Button(name='ACRsel',color=BLACK,
                    topleft=(cont.REGLED2.left,cont.REGLED0.bottom+50),size = 20,
                    value=0,label='ACR',
                    group='REGselect',groupaction='RADIO')
  Controls.REGSELS += [cont.ACRsel] # add to list of PCRLEDS as a object



  cont.IXRsel = Button(name='IXRsel',color=BLACK,
                    topleft=(cont.ACRsel.left,cont.ACRsel.bottom+10),size = 20,
                    value=0,label='IXR',
                    group='REGselect',groupaction='RADIO')
  Controls.REGSELS += [cont.IXRsel] # add to list of PCRLEDS as a object

  cont.MBRsel = Button(name='MBRsel',color=BLACK,
                    topleft=(cont.ACRsel.left,cont.IXRsel.bottom+10),size = 20,
                    value=0,label='MBR',
                    group='REGselect',groupaction='RADIO')
  Controls.REGSELS += [cont.MBRsel] # add to list of PCRLEDS as a object
  cont.MBRsel.toggle()   # default to this button selected
  
  cont.INRsel = Button(name='INRsel',color=BLACK,
                    topleft=(cont.ACRsel.left+75,cont.ACRsel.top),size = 20,
                    value=0,label='INR',
                    group='REGselect',groupaction='RADIO')
  Controls.REGSELS += [cont.INRsel] # add to list of PCRLEDS as a object

  cont.MARsel = Button(name='MARsel',color=BLACK,
                    topleft=(cont.INRsel.left,cont.INRsel.bottom+10),size = 20,
                    value=0,label='MAR',
                    group='REGselect',groupaction='RADIO')
  Controls.REGSELS += [cont.MARsel] # add to list of PCRLEDS as a object
  
  cont.MSRsel = Button(name='MSRsel',color=BLACK,
                    topleft=(cont.MARsel.left,cont.MARsel.bottom+10),size = 20,
                    value=0,label='MSR',
                    group='REGselect',groupaction='RADIO')
  Controls.REGSELS += [cont.MSRsel] # add to list of PCRLEDS as a object

# define the enter and display buttons
  cont.displayLED = Led(name='displayLED',color=BLACK,
              topleft = (cont.REGLED6.left,cont.MBRsel.top),size=30,
              label='Display',app_handler=displayled_handler,
              state = 'OFF',oncolor=BLACK,offcolor=WHITE)

  cont.enterLED = Led(name='enterLED',color=BLACK,
              topleft = (cont.displayLED.left+125,cont.MBRsel.top),size=30,
              label='Enter',app_handler=enterled_handler,
              state = 'OFF',oncolor=BLACK,offcolor=WHITE)

# define the four sense switches

  cont.sense0 = Button(name='sense0',color=BLACK,
                    topleft=(cont.REGLED11.left,cont.REGLED9.bottom+90),size = 20,
                    value=0,label='Sense0')
  cont.SENSELEDS += [cont.sense0]  # add to the list of sense switch leds

  cont.sense1 = Button(name='sense1',color=BLACK,
                    topleft=(cont.sense0.left,cont.sense0.bottom+10),size = 20,
                    value=0,label='Sense1')
  cont.SENSELEDS += [cont.sense1]  # add to the list of sense switch leds
  
  cont.sense2 = Button(name='sense2',color=BLACK,
                    topleft=(cont.sense0.left+150,cont.sense0.top),size = 20,
                    value=0,label='Sense2')
  cont.SENSELEDS += [cont.sense2]  # add to the list of sense switch leds
  
  cont.sense3 = Button(name='sense3',color=BLACK,
                    topleft=(cont.sense2.left,cont.sense2.bottom+10),size = 20,
                    value=0,label='Sense3')
  cont.SENSELEDS += [cont.sense3]  # add to the list of sense switch leds
  
# the clearall LED

  cont.clrstLED = Led(name='clearLED',color=BLACK,
              topleft = (cont.clrREGLED.left,cont.MBRsel.top),size=30,
              label='Clear',app_handler=clearled_handler,
              state = 'OFF')

# the run/halt LED
  cont.runLED =Led(name='runLED',color=BLACK,
              topleft = (cont.clrREGLED.left+125,cont.MBRsel.top),size=30,
              label='RUN/HALT',app_handler=runled_handler,
              state = 'OFF',oncolor=GREEN,offcolor=RED)


# the step LED (same as single command on original)

  cont.stepLED =Led(name='STEPLED',color=BLACK,
              topleft = (cont.runLED.left+150,cont.MBRsel.top),size=30,
              label='STEP',app_handler=stepled_handler,
              state = 'OFF',oncolor=GREEN,offcolor=RED) 


  
  return cont # return the controls object


  
"""**************** Main Program ****************************"""
# draw and initialize the controls portion of the machine

cont = init_controls()

core = Core()
#--------------------------------------------------------------
# Top of main program loop 
#--------------------------------------------------------------

while True:

  # if in step mode, execute one instruction and then reset step
  if (cont.stepLED.state == 'ON'):
    alu_execute(1)
    cont.stepLED.toggle()
  elif (cont.runLED.state == 'ON'):
    start = time.perf_counter()
    halt = alu_execute(100000+random.randint(-100,+100))   # execute about 100000 instructions before returning
    runtime= time.perf_counter()- start
#    print (runtime)
    if (halt):
      cont.runLED.toggle()
  # update the control panel with the current state of things

  cont.updatePCRLEDS()  # show the program counter
  cont.updateREGLEDS()  # show the selected register


 
  # check for the QUIT  or mouse event
  for event in pygame.event.get():
      if event.type == QUIT:
          pygame.quit()
          sys.exit()

      if event.type == MOUSEBUTTONDOWN:
          pos = pygame.mouse.get_pos() # mouse clicked get (x, y)

          # check through widget dictionary and call handler if clicked
          for widgetname in Widget.widgetlist:
              widget_object = Widget.find_widget(widgetname)

              if widget_object.isclicked(pos):
                  widget_object.handler()


  




  # End of program loop

