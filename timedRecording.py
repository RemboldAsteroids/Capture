#===================================================
#
# File Name: timedRecording.py
# 
# Purpose: To record footage during a set time interval 
#
# Creation Date: 05-06-2017
#
# Last Modified: Thu 31 May 2018 05:26:32 PM PDT
#
# Created by: Jed Rembold
#
#===================================================

'''
Script should check the local clock to a set time interval and
if within that time interval, should record. Written with the
intention of being used to capture known events (Iridium
flares) for finetuning of analysis and capture software.
'''

import argparse
from VidUtils import KeyClipWriter
from datetime import datetime, timedelta
from dateutil import parser
import cv2
import time

def initializeVideo(src):
    kcw = KeyClipWriter()
    cam = cv2.VideoCapture(src)
    return kcw, cam

def parseArgs():
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '--start', help='Time and date to start recording')
    ap.add_argument('-e', '--end', help='Time and date to end recording')
    ap.add_argument('-o', '--output', help='Path to save video to')
    ap.add_argument('--src', default=0, help='Video Source Number. Defaults to 0')
    args = vars(ap.parse_args())
    return args


def printTimeRemaining(endtime):
    timeleft = (endtime - datetime.now()).total_seconds()
    if not round(timeleft,1) % 1:
        # print(f'\rRecording Time Left: {int(timeleft):5} seconds', end='', flush=True)
        print('\rTime left: {:5} seconds'.format(int(timeleft)), end='', flush=True)

def main():
    args = parseArgs()

    starttime = parser.parse(args['start'])
    endtime = parser.parse(args['end'])
    src = int(args['src'])
    print('Recording to start at: {}'.format(datetime.strftime(starttime,"%Y/%m/%d %I:%M:%S")))
    print('Recording to end at: {}'.format(datetime.strftime(endtime,"%Y/%m/%d %I:%M:%S")))

    kcw, cam = initializeVideo(src)

    #Sleep until starting time, periodically checking time
    while starttime > datetime.now():
        timetill = (starttime - datetime.now()).total_seconds()
        # frame = cam.read()[1]
        if not round(timetill,1) % 1:
            print('\rTime until recording begins: {:5} seconds'.format(int(timetill)), end='', flush=True)

    #Wake up and start!
    print('\n---- Video recording starting! ----')

    while datetime.now() <= endtime:
        frame = cam.read()[1]
        cv2.putText(frame,
                datetime.now().strftime('%Y%m%d_%H%M%S.%f'),
                (10, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (125,125,125),
                )
        kcw.update(frame)

        if not kcw.recording:
            path = "{}/{}.avi".format(args['output'], datetime.now().strftime('%Y%m%d_%H%M%S'))
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            kcw.start(path, fourcc, 30)

        printTimeRemaining(endtime)

    #All done! Shut things down!
    print('\n---- Recording Complete ----')
    if kcw.recording:
        kcw.finish()


if __name__ == '__main__':
    main()
    


