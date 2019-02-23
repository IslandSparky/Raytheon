""" Test program for memory read/write """

import sys, time , random , math , serial
MAXMEMORY = 32768
MEMORY = []     # set up the memory array
for i in range(MAXMEMORY):
  MEMORY.append(0x0000)

# store a few values in memory

MEMORY[0] = 0Xffff
MEMORY[1] = 1
MEMORY[2] = 2
MEMORY[3] = 3
MEMORY[4] = 4
MEMORY[5] = 5
MEMORY[MAXMEMORY-1] = 0xE0f  
# open a binary file

with  open("memory.dat", "w") as memory_file:
  for i in range(MAXMEMORY):
    memory_file.write(hex(MEMORY[i]) )
    memory_file.write('\n')
                   

for i in range(MAXMEMORY):
  MEMORY[i] = 0
with open("memory.dat", "r") as memory_file:
  for i in range(MAXMEMORY):
    MEMORY[i] = memory_file.readline()
    MEMORY[i] = MEMORY[i][0:-1]      # remove trailing new line
    MEMORY[i] = int(MEMORY[i],0)



print (MEMORY[0])
print (MEMORY[1])
MEMORY[1] = MEMORY[1] + 1  # insure we are back to integer
print (MEMORY[1])
print (MEMORY[MAXMEMORY-1])

