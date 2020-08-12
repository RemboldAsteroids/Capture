#===================================================
#
# File Name: gui.py
# 
# Purpose: Urwid Observation Control Assembly
#
# Creation Date: 19-05-2017
#
# Last Modified: Tue 30 May 2017 03:58:40 PM PDT
#
# Created by: Jed Rembold
#
#===================================================

import urwid
import subprocess
import time
import shutil
import tailer  # may need to install from pip
import motionprocess
import logging
from threading import Thread

import shared


# Template for shared config file writing
template = """'''
Shared config file for gui and
motionprocess to read and write to.
'''

RUNNING = False
ANALYZE_ON = False
SAVELOC = '{loc}'
LATITUDE = {lat}
LONGITUDE = {long}
STARTTIME = {stime}
ENDTIME = {etime}
BRIGHT_THRESH = {b_thresh}
FRAMERATE = 0
SRC = {src}
TEMP = {temp}
HUMID = {humid}

class DETECT:
    LENGTH = {len}
    ANGLES = {angs}
    THRESHOLD = {thresh}
    MINLINE = {mlin}
    LINESKIP = {lskip}
"""

# Globals
mainprog = None #Needs to be global so that subsequent
                #handle_keypress calls still understand

#Setting up logging formatting and location
#logging.basicConfig(
#        #Logging to Log.txt in same directory as script
#        filename = 'Logs/Observation_Log.log',
#        level = logging.DEBUG,
#        style = '{',
#        format = '[{asctime}.{msecs:<3.0f}] ' +
#                 '[{levelname:^8}]: {message}',
#        datefmt = '%Y/%m/%d %H:%M:%S',
#        # filemode = 'w',
#        )

def writeConfig():

    with open('shared.py', 'w') as f:
        content = {
                'loc': shared.SAVELOC,
                'stime': shared.STARTTIME,
                'etime': shared.ENDTIME,
                'src': shared.SRC,
                'b_thresh': shared.BRIGHT_THRESH,
                'len': shared.DETECT.LENGTH,
                'angs': shared.DETECT.ANGLES,
                'thresh': shared.DETECT.THRESHOLD,
                'mlin': shared.DETECT.MINLINE,
                'lskip': shared.DETECT.LINESKIP,
                'temp': shared.TEMP,
                'humid': shared.HUMID,
                'long': shared.LONGITUDE,
                'lat': shared.LATITUDE,
                }
        f.write(template.format(**content))

def handle_keypress(key):
    '''
    Function to handle all keypresses on terminal
    Should account for any hotkeys necessary
    '''
    global mainprog

    if key in ('q', 'Q'):
        writeConfig()
        raise urwid.ExitMainLoop()

    if key in ('1'):
        mainprog = Thread(target=motionprocess.analyze,
                args=(60,shared.SAVELOC,True))
        mainprog.daemon = True
        mainprog.start()
        shared.RUNNING = True

    if key in ('2'):
        shared.RUNNING = False
        mainprog.join()

    if key in ('3'):
        # Drawing and handling the pop-up window
        starttimetext = urwid.IntEdit(
                caption='Enter Daylight Starting Hour: ')
        starttime_wrap = urwid.Padding(starttimetext,
                align='center', left=5, right=5)
        starttimedone = urwid.Padding(
                urwid.Button('Done!', 
                    saveStartTime, user_data=starttimetext),
                align='center', width=12)
        starttimeprompt =   urwid.LineBox(
                            urwid.Filler(
                            urwid.Pile([starttime_wrap, 
                                starttimedone])
                            ), 
                            title='Set Starting Hour',
                            )
        starttimefill = urwid.AttrMap(starttimeprompt, 'general')
        loop.widget = urwid.Overlay(starttimefill, 
                everything, align='center', 
                width=('relative', 60), valign='middle', 
                height=('relative', 20))


    if key in ('4'):
        # Drawing and handling the pop-up window
        stoptimetext = urwid.IntEdit(
                caption='Enter Daylight Ending Hour: ')
        stoptime_wrap = urwid.Padding(stoptimetext, 
                align='center', left=5, right=5)
        stoptimedone = urwid.Padding(
                urwid.Button('Done!', 
                    saveEndTime, user_data=stoptimetext),
                align='center', width=12)
        stoptimeprompt =   urwid.LineBox(
                           urwid.Filler(
                           urwid.Pile([stoptime_wrap, stoptimedone])
                           ),
                           title='Set Stopping Hour',
                           )
        stoptimefill = urwid.AttrMap(stoptimeprompt, 'general')
        loop.widget = urwid.Overlay(stoptimefill, 
                everything, align='center', 
                width=('relative', 60), valign='middle', 
                height=('relative', 20))

    if key in ('5'):
        # Drawing and handling the pop-up window 
        fileloctext = urwid.Edit(
                caption='Full File Folder Path: ')
        fileloctext_wrap = urwid.Padding(
                fileloctext, align='center', left=5, right=5)
        filelocdone = urwid.Padding(
                urwid.Button('Done!', saveFileLoc, 
                    user_data=fileloctext),
                align='center', width=12)
        filelocprompt  =   urwid.LineBox(
                           urwid.Filler(
                           urwid.Pile([fileloctext_wrap, filelocdone])
                           ),
                           title='Set New File Location',
                           )
        fileloc_wrap = urwid.AttrMap(filelocprompt, 'general')
        loop.widget = urwid.Overlay(
                fileloc_wrap, everything, 
                align='center', width=('relative', 60), 
                valign='middle', height=('relative', 20))

def saveStartTime(button, textfield):
    '''
    Function to handle pressing done when
    adjusting the start analysis time. Will
    not quit if start time is after end time
    '''

    def restoreButton(loop, userdat):
        ''' 
        Quick function to reset the button
        text if an error occurs.
        '''
        button.set_label(('general', 'Done!'))

    # global STARTTIME
    fieldcheck = textfield.value()
    if fieldcheck < shared.ENDTIME and fieldcheck > 0:
        shared.STARTTIME = textfield.value()
        loop.widget = everything
    else:
        button.set_label(('alert', 'Error!'))
        button._label.align = 'center'
        loop.set_alarm_in(1, restoreButton )

def saveEndTime(button, textfield):
    '''
    Function to handle pressing done when
    adjusting the end analysis time. Will
    not quit if end time is before start time
    '''
    
    def restoreButton(loop, userdat):
        '''
        Quick function to reset the button text 
        if an error occurs.
        '''
        button.set_label(('general', 'Done!'))

    fieldcheck = textfield.value()
    if fieldcheck > shared.STARTTIME and fieldcheck < 24:
        shared.ENDTIME = textfield.value()
        loop.widget = everything
    else:
        button.set_label(('alert', 'Error!'))
        loop.set_alarm_in(1, restoreButton)



def saveFileLoc(button, textfield):
    '''
    Function to handle pressing done when
    changing the file location to save data
    '''
    shared.SAVELOC = textfield.get_edit_text()
    loop.widget = everything

def updatedat(loop, user_dat):
    ''' 
    Function to update the event log
    May be able to combine with with below status updates
    '''
    msgtxt.set_text(parse_log())
    loop.set_alarm_in(5, updatedat)

def updatestatus(loop, userdat):
    '''
    Function to periodically update all the
    status line entries.
    '''
    #Update Time
    st_time.set_text(['Time: ', 
        ('general', 
            time.strftime('%H:%M:%S', time.localtime())+'\n')
        ])

    #Update Running
    if shared.RUNNING:
        st_running.set_text(['Running: ', ('info', 'On\n')])
    else:
        st_running.set_text(['Running: ', ('alert', 'Off\n')])

    #Update Analyzing
    if shared.ANALYZE_ON:
        st_analyzing.set_text(['Analyzing: ', ('info', 'On\n')])
    else:
        st_analyzing.set_text(['Analyzing: ', ('alert', 'Off\n')])

    #Update Daylight Start and Stop
    st_daystart.set_text(['Daylight Start: ', 
        ('general', str(shared.STARTTIME)+'\n')])
    st_dayend.set_text(['Daylight End: ', 
        ('general', str(shared.ENDTIME))])

    #Update Disk Location
    st_saveloc.set_text(['Save Location: ', 
        ('general', shared.SAVELOC), '\n'])

    #Update Disk Space
    try:
        dspace = shutil.disk_usage(shared.SAVELOC).free*1E-9
        if dspace > 0.5:
            st_diskspace.set_text(['Free Space: ', 
                ('info', str(round(dspace))+' GB\n')])
        else:
            st_diskspace.set_text(['Free Space: ', 
                ('alert', str(round(dspace))+' GB\n')])
    except:
        st_diskspace.set_text(['Free Space: ', 
            ('alert', 'File not found!\n')])

    #Update Frame Rate
    if shared.ANALYZE_ON and shared.FRAMERATE:
        st_framerate.set_text(['Frame Rate: ', 
            ('info',  '{:0.2f}\n'.format(shared.FRAMERATE))])
    else:
        st_framerate.set_text(['Frame Rate: ', ('alert', 'N/A\n')])

    #Update Temperature and Humidity
    if shared.TEMP == 'NA':
        st_temp.set_text(['Temperature: ', ('info', 'N/A\n')])
        st_humid.set_text(['Humidity: ', ('info', 'N/A\n')])
    else:
        st_temp.set_text(['Temperature: ', ('info', '{:0.2f}F\n'.format(shared.TEMP))])
        st_humid.set_text(['Humidity: ', ('info', '{:0.2f}%\n'.format(shared.HUMID))])

    loop.set_alarm_in(1, updatestatus)


def parse_log():
    '''
    Function responsible for reading the 4 most recent
    lines of the observation log file, parsing them and
    returning the colored variants ready for screen
    display
    '''
    output = []
    try:
        log_data = tailer.tail(open('Logs/Observation_Log.log'), 4)
    except:
        return [('alert', 'File Not Found!')]
    if log_data:
        for line in log_data:
            date, ctype, mess = line.split(']')
            date = date[12:]
            ctype= ctype[2:].strip()
            mess = mess[2:]
            output.append([
                ('info', ctype+': '), 
                ('general', date), ('\n'), 
                ('boxes', mess), ('\n\n')])
        return output
    else:
        return [('alert', 'Log File Empty')]


palette = [
        ('boxes', 'dark cyan', ''),
        ('info', 'dark green', ''),
        ('alert', 'dark red', ''),
        ('general', 'light gray', ''),]


#------------------------------
#Left Column
#------------------------------
cmdtxt = urwid.Text([
    ('general', "1. "), ('boxes', "Start Main"), ('\n\n'),
    ('general', "2. "), ('boxes', "Stop Main"), ('\n\n'),
    ('general', "3. "), ('boxes', "Set Start Time"), ('\n\n'),
    ('general', "4. "), ('boxes', "Set Stop Time"), ('\n\n'),
    ('general', "5. "), ('boxes', "Set Save Location"), ('\n\n'),
    ('general', "q. "), ('boxes', "Exit"),], align='left')
menubox = urwid.LineBox(
        urwid.Padding(urwid.Filler(cmdtxt), left=3, right=3),
        title='Menu')
menubox_wrap = urwid.AttrMap(menubox, 'boxes')


#------------------------------
#Right Column
#------------------------------
# Message Log
msgtxt = urwid.Text('Message Log Display', align='left')
msgbox = urwid.LineBox(
        urwid.Padding(
            urwid.Filler(msgtxt, 'top', top=1, bottom=0), 
            left=1, right=1), 
        title="Recent Events")
msgbox_wrap = urwid.AttrMap(msgbox, 'boxes')

# Status Box
#lhs
st_running = urwid.Text('Running: \n')
st_analyzing = urwid.Text('Analyzing: \n')
st_time = urwid.Text('Time: \n')
st_daystart = urwid.Text('Daylight Start: \n')
st_dayend = urwid.Text('Daylight End: ')
st_lhs = urwid.Pile([st_time, 
    st_running, st_analyzing, st_daystart, st_dayend])

#rhs
st_saveloc = urwid.Text('Save Location: \n')
st_diskspace = urwid.Text('Free Space: \n')
st_framerate = urwid.Text('Frame Rate: \n')
st_temp = urwid.Text('Temperature: \n')
st_humid = urwid.Text('Humidity: \n')
st_rhs = urwid.Pile([st_saveloc, st_diskspace, st_framerate, st_temp, st_humid])

statusbox = urwid.LineBox(
        urwid.Padding(
            urwid.Filler(urwid.Columns([st_lhs,st_rhs])), 
            left=1, right=1), 
        title='Current Status')
statusbox_wrap = urwid.AttrMap(statusbox, 'boxes')

#Stacking Message box and status box
screen_rhs = urwid.Pile([msgbox_wrap, statusbox_wrap])

# Putting all together
everything = urwid.Columns([menubox_wrap, ('weight', 2, screen_rhs)])

# Main loop and initial alarms
loop = urwid.MainLoop(everything, palette, 
        unhandled_input=handle_keypress)
loop.set_alarm_in(0, updatedat)
loop.set_alarm_in(0, updatestatus)
loop.run()

