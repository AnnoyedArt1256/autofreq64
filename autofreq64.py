#!/usr/bin/env python3
# autofreq64: a small C64 utility for modifiying SID frequency tables
# made by AArt1256 in 23/01/2025
# 
# Copyright (c) 2025 AnnoyedArt1256
# 
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
# 
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import sys
from pathlib import Path
import math

NEW_A_440 = 424*2**(1.0/12.0)#440 #424*2**(1.0/12.0)

one_semitone = 2**(1.0/12.0)

def diff(a,b):
    return abs(a-b)

def sid2hz(freq):
    return (freq*985248.0)/(256**3)

def hz2sid(freq):
    cnst = (256**3)/985248.0 # PAL frequency
    return min(max(math.floor(freq*cnst),0),0xffff)

def freqToNote(freq):
    return (12.0*math.log2(freq/440.0))+69.0

def noteToFreq(note):
    return (NEW_A_440 / 32.0) * (2**((note - 9) / 12.0))

def noteToFreq_440(note):
    return (440.0 / 32.0) * (2**((note - 9) / 12.0))

def check_no_interleave(data):
    matches = []
    for freq_lo_off in range(len(data)-6):
        # fix sidtracker64 freq tables from not being detected...
        hi_off_max = min((len(data)-6)-freq_lo_off,640) 
        for freq_hi_off in range(freq_lo_off+6,freq_lo_off+hi_off_max):
            is_table = 1
            for ind in range(1,32):
                # fixed out of bounds problems (sidtracker64)
                try:
                    freq_prev = data[freq_lo_off+ind-1]+(data[freq_hi_off+ind-1]*256)
                    freq = data[freq_lo_off+ind]+(data[freq_hi_off+ind]*256)
                except:
                    break
                # also allow very minute freq differences
                if freq_prev != 0:
                    if diff((freq/freq_prev),one_semitone) > 0.01:
                        is_table = 0
                        break
                else:
                    is_table = 0
                    break
            if is_table == 1:
                print("possible match? (no-interleave): ",hex(freq_lo_off+0x7E),hex(freq_hi_off+0x7E))
                matches.append([freq_lo_off,freq_hi_off])

            is_table = 1
            for ind in range(1,32):
                # fixed out of bounds problems (sidtracker64)
                try:
                    freq_prev = data[freq_hi_off+ind-1]+(data[freq_lo_off+ind-1]*256)
                    freq = data[freq_hi_off+ind]+(data[freq_lo_off+ind]*256)
                except:
                    break
                # also allow very minute freq differences
                if freq_prev != 0:
                    if diff((freq/freq_prev),one_semitone) > 0.01:
                        is_table = 0
                        break
                else:
                    is_table = 0
                    break
            if is_table == 1:
                print("possible match? (no-interleave): ",hex(freq_lo_off+0x7E),hex(freq_hi_off+0x7E))
                matches.append([freq_hi_off,freq_lo_off])

    match_dict = {}
    # seperate matches by freq-table lengths
    for i in matches:
        if abs(i[1]-i[0]) not in match_dict:
            match_dict[abs(i[1]-i[0])] = []
        match_dict[abs(i[1]-i[0])].append(i)

    # for memory reasons i guess :3
    del matches

    matches = []

    for i in match_dict:
        # if there isn't enough matches, then skip it
        if len(match_dict[i]) < 2:
            continue

        # now check if a group of matches is valid 
        # (by checking for consectutive matches)
        is_valid = 0
        valid_pos = None
        pos_len = 0

        for table_pos in match_dict[i]:
            is_pos_valid = 1
            for ind in range(1,min(max(i-56,12),256)):
                if [table_pos[0]+ind,table_pos[1]+ind] not in match_dict[i]:
                    pos_len = ind
                    is_pos_valid = 0
                    break
            if is_pos_valid == 1 or (pos_len > 24):
                is_valid = 1
                valid_pos = table_pos
                break

        if is_valid == 1:
            # now let's make our guessed freq table position more accurate
            # by checking for neighboring addresses
            valid_pos_thres = []
            for ind in range(-32,32):
                # fix sidtracker64
                try:
                    freq_prev = data[valid_pos[0]+ind-1]+(data[valid_pos[1]+ind-1]*256)
                    freq = data[valid_pos[0]+ind]+(data[valid_pos[1]+ind]*256)
                    # to avoid division by zero errors...
                    if freq_prev == 0:
                        valid_pos_thres.append(False)
                    else:
                        valid_pos_thres.append(diff((freq/freq_prev),one_semitone) > 0.01)
                except:
                    valid_pos_thres.append(False)

            for ind_pos in range(0,len(valid_pos_thres)-2):
                if (valid_pos_thres[ind_pos] == True and
                   valid_pos_thres[ind_pos+1] == False and
                   not valid_pos_thres[ind_pos+2] == True): # just for good measure
                    valid_pos[0] += ind_pos-32
                    valid_pos[1] += ind_pos-32
                    break

            # change freq-table length if pos_len is big enough
            if pos_len > 24:
                i = pos_len+32

            print("\n\n")
            print("found possible freq table (no-interleave) at pos [lo, hi]",valid_pos)
            print("with len",i)
            print("\n\n")
            matches.append([valid_pos,i])
            break
    try:
        return matches[0]
    except:
        return -1

def check_interleave(data):
    matches = []
    for freq_lo_off in range(len(data)-256):
        # little-endian
        is_table = 1
        for ind in range(1,32):
            freq_prev = data[freq_lo_off+(ind-1)*2]+(data[freq_lo_off+(ind-1)*2+1]*256)
            freq = data[freq_lo_off+ind*2]+(data[freq_lo_off+ind*2+1]*256)
            # also allow very minute freq differences
            if freq_prev != 0:
                if diff((freq/freq_prev),one_semitone) > 0.05:
                    is_table = 0
                    break
            else:
                is_table = 0
                break
        if is_table == 1:
            print("possible match? (interleave): ",hex(freq_lo_off+0x7E))
            matches.append(freq_lo_off)

    match_offs = matches

    matches = []

    for i in match_offs:
        valid_len = 0
        for ind in range(1,256):
            if (i+ind*2) not in match_offs:
                valid_len = ind+32
                break

        if valid_len > 6:
            print("\n\n")
            print("found possible freq table (interleave) at pos",i)
            print("with len",valid_len)
            print("\n\n")
            matches.append([i,valid_len])
            break
    try:
        return matches[0]
    except:
        return -1

if len(sys.argv) < 2:
    print("not enough arguments supplied")
else:
    o = open(Path(sys.argv[1]).stem+"_MODIFIED_TABLE.sid","wb")
    f = open(sys.argv[1],"rb").read()
    
    header = list(f[:0x7E])
    data = list(f[0x7E:])
    o.write(bytearray(header))

    # try checking for freq tables laid out like this
    # LLLLLL ... LLLLLL HHHHHH ... HHHHHH
    # (i.e. first the low bytes, then the high bytes)

    matches = check_no_interleave(data)
    print(matches)
    if matches == -1:
        # try checking for freq tables laid out like this
        # LHLHLHLHLH ... LHLHLHLHLH
        # (i.e. interleaving between the low and high bytes)
        matches = check_interleave(data)
        if matches == -1:
            print("how did you get here?")
        else:
            freq_pos = matches[0]
            freq_len = matches[1]
            first_freq = data[freq_pos]+(data[freq_pos+1]*256)
            print(first_freq)
            first_freq = round(freqToNote(sid2hz(first_freq)))
            for i in range(freq_len):
                freq = hz2sid(noteToFreq(float(first_freq+i)))
                if freq_pos+i*2 < len(data):
                    data[freq_pos+i*2] = freq&0xff # lo byte
                if freq_pos+i*2+1 < len(data):
                    data[freq_pos+i*2+1] = (freq>>8)&0xff # hi byte
    else:   
        freq_pos = matches[0]
        freq_len = matches[1]
        first_freq = data[freq_pos[0]]+(data[freq_pos[1]]*256)
        print(first_freq)
        first_freq = round(freqToNote(sid2hz(first_freq)))
        for i in range(freq_len):
            freq = hz2sid(noteToFreq(float(first_freq+i)))
            if freq_pos[0]+i < len(data):
                data[freq_pos[0]+i] = freq&0xff # lo byte

            if freq_pos[1]+i < len(data):
                data[freq_pos[1]+i] = (freq>>8)&0xff # hi byte

    o.write(bytearray(data))
    o.close()
