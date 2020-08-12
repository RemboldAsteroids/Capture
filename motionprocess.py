# ===================================================
#
# File Name: motionprocess.py
#
# Purpose: Find and record fireball events in grayscale
#
# Creation Date: 16-01-2017
#
# Last Modified: Wed 28 Jun 2017 04:25:58 PM PDT
#
# Created by: Jed Rembold
#
# ===================================================

import argparse
from VidUtils import KeyClipWriter, ShortClipWriter
from datetime import datetime as dt
import time
import os
import sys
import logging
import shutil
import numpy as np
import cv2
import csv
import string
import dbfuncs as dbf

# import cProfile
from threading import Thread

TempLog = True
try:
    from HumTemp import log_weather
except ImportError:
    TempLog = False

import shared

d6log = logging.getLogger("D6")
format_ = "[{asctime}.{msecs:<3.0f}] [{levelname:^8}]: {message}"
fhandler = logging.FileHandler("Logs/Observation_Log.log")
fhandler.setFormatter(
    logging.Formatter(format_, datefmt="%Y/%m/%d %H:%M:%S", style="{")
)
d6log.setLevel(logging.DEBUG)
d6log.addHandler(fhandler)


def next_id(prev_id: string = None) -> str:
    if prev_id == None:
        old = 0
    else:
        old = base36decode(prev_id)
    return base36encode(old + 1)


def base36encode(number: int) -> str:
    if not isinstance(number, int):
        raise TypeError("Number must be an integer")

    if number < 0:
        raise ValueError("Number must be positive")

    alphabet = string.digits + string.ascii_uppercase
    base36 = ""

    if 0 <= number < len(alphabet):
        return alphabet[number].rjust(3, "0")

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return base36.rjust(3, "0")


def base36decode(input: str) -> int:
    return int(input, 36)


def takeSnapshot(path: str):
    """
    Function to be run in a thread to take periodic snapshots of the
    night sky. Mainly to serve as a confirmation for the sky state
    at any particular hour of the night
    """
    while True:
        while grabbed and shared.ANALYZE_ON:
            date_num = dt.utcnow()
            date_str = date_num.strftime("%Y%m%d_%H%M%S")
            if avg is not None:
                savefile = cv2.resize(
                    avg, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
                )
                cv2.imwrite(path + "/" + date_str + "_Snap.png", savefile)
                d6log.info("Taking Snapshot: {}_Snap.png".format(date_str))
            time.sleep(10 * 60)  # Sleep 30 mins
        time.sleep(5 * 60)  # If analysis off, wait 10 minutes then check again


def weightaccum(old_frame, new_frame, weight):
    """ Function calculates an accumulated weighted average. This function
    serves as a wrapper to the basic script to recast the arrays in the
    needed datatype. """
    # Recasting in float32 as accumulateWeighted requires this datatype
    old_frame = old_frame.astype(np.float32)
    new_frame = new_frame.astype(np.float32)
    # Doing the weighted average
    cv2.accumulateWeighted(new_frame, old_frame, weight)
    # Returning the result cast back in uint8
    return old_frame.astype(np.uint8)


def drawBoundingHough(frame, x1, x2, y1, y2):
    """ Function to draw a red box around all detected objects in a scene
    """
    size = 40
    midx = int((x2 + x1) / 2)
    midy = int((y2 + y1) / 2)
    p1x = max(midx - size, 0)
    p1y = max(midy - size, 0)
    p2x = min(midx + size, frame.shape[1])
    p2y = min(midy + size, frame.shape[0])
    cv2.rectangle(frame, (p1x, p1y), (p2x, p2y), 255, 1)


def get_Hough_Avg_Pt(lines):
    x1, y1, x2, y2 = lines[0]
    return (int((x1 + x2) / 2), int((y1 + y2) / 2))


def write_to_table(pos: "(x,y)"):
    with open("Logs/Obs_Table.csv", "r") as f:
        row = next(reversed(list(csv.reader(f))))
        code = row[0]

    params = {
        "code": next_id(code),
        "local": dt.strftime(dt.now(), "%Y%m%d %H:%M:%S"),
        "utc": dt.strftime(dt.utcnow(), "%Y%m%d %H:%M:%S"),
        "ptx": pos[0],
        "pty": pos[1],
    }

    with open("Logs/Obs_Table.csv", "a") as f:
        f.write("{code},{local},{utc},{ptx},{pty}\n".format(**params))

def finish_session(sessionid):
    start_time = dbf.get_entry(sessionid, 'start_time_utc')
    end_time = dt.utcnow()
    diff = (end_time - start_time).total_seconds()
    dbf.update_session(sessionid, {
        "end_time_utc": end_time,
        "end_time_local": dt.now(),
        "elapsed_time": diff,
        })


def analyze(buffsize, savepath, headless, vpath=None, delay=1):
    """
    This is the main analysis script. Reads in the data from the camera,
    checks for objects, opens threads to save the data if an object is
    found. """

    global grabbed, avg, frame

    # Saved video or live video?
    if vpath is None:
        # Must be live video
        cam = cv2.VideoCapture(shared.SRC)
        time.sleep(1.0)
    else:
        # Must be saved video
        cam = cv2.VideoCapture(vpath)

    # Initializing everything
    avg = None
    accum = None
    framenum = 0
    kcw = ShortClipWriter(bufSize=buffsize)
    consecFrames = 0
    d6log.info("New Observation Run Started")
    d6log.info(
        "Detection params -- Length: {}, Threshold: {}, MinLine: {}, LineSkip: {}".format(
            shared.DETECT.LENGTH,
            shared.DETECT.THRESHOLD,
            shared.DETECT.MINLINE,
            shared.DETECT.LINESKIP,
        )
    )
    d6log.info("Clips saved to {}".format(savepath))

    disk_full = False

    # Grab one frame to initialize
    (grabbed, frame) = cam.read()

    # Start snapshoting thread
    snapshots = Thread(target=takeSnapshot, args=(savepath,))
    snapshots.daemon = True
    snapshots.start()

    # Start weather logging thread
    if TempLog:
        weather = Thread(target=log_weather, args=(5 * 60,))
        weather.daemon = True
        weather.start()

    while grabbed:
        # Check the time to see what hour of the day it is
        curr_hour = time.localtime().tm_hour

        if vpath is not None:
            shared.ANALYZE_ON = True
        else:
            # If it is nighttime turn on analyzing, else sleep for 5 mins
            # before checking again
            if not shared.STARTTIME <= curr_hour < shared.ENDTIME:
                shared.ANALYZE_ON = True
                d6log.info("A new night has arrived! Frame analysis beginning!")
                lastid = dbf.get_last_session_id()
                if lastid is not None:
                    newid = next_id(lastid[1:])
                else:
                    newid = next_id(lastid)
                sessionid = "s" + newid
                dbf.add_session(sessionid)
                dbf.update_session(
                    sessionid,
                    {
                        "start_time_utc": dt.utcnow(),
                        "start_time_local": dt.now(),
                        "ht_length": shared.DETECT.LENGTH,
                        "ht_thresh": shared.DETECT.THRESHOLD,
                        "ht_minline": shared.DETECT.MINLINE,
                        "ht_lineskip": shared.DETECT.LINESKIP,
                        "bright_thresh": shared.BRIGHT_THRESH,
                        "latitude": shared.LATITUDE,
                        "longitude": shared.LONGITUDE,
                    },
                )

            else:
                # print("Daylight! Sleeping...")
                time.sleep(5)

        # When analyzing is turned on
        while shared.ANALYZE_ON:
            # Grab the current time for fps purposes
            startframetime = time.time()

            # Grab the latest frame
            (grabbed, frame) = cam.read()

            # If no frame to grab, either we have an issue or we are at the end
            if not grabbed:
                d6log.warning("No frame was grabbed. Exiting run loop.")
                break

            # Initialize frame as no containing an event, so that consecutive
            # non-event frame counter should augment
            updateConsecFrames = True

            # Process Frame
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            B = gray.copy()

            # Resize grayscale image for faster image processing
            # (reducing each dimension by a factor of 2)
            gray = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

            # Average Frame
            if avg is None:
                avg = gray.copy()
            # Using a very small weighted average to vastly prefer older
            # frames that do not include any current fireballs,
            # thereby creating our background
            avg = weightaccum(avg, gray, 0.05)

            # Subtract and Threshold
            delta = cv2.subtract(gray, avg)
            thresh = cv2.threshold(delta, shared.BRIGHT_THRESH, 255, cv2.THRESH_BINARY)[1]
            kernel = np.ones([2, 2])
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

            # Accumulated binaries to create line for Hough transform to find
            if accum is None:
                accum = thresh.copy()
            # Using a larger weighted average to create a composite of the
            # more recent frames, which should include the fireball trail
            accum = weightaccum(accum, thresh, 0.1)
            # Thresholding the accumulated image for Hough Transforming
            accum_thresh = cv2.threshold(accum, 10, 255, cv2.THRESH_BINARY)[1]

            # Writing date and time in UTC to lower left corner of
            # output frame in green
            date_num = dt.utcnow()
            date_str = date_num.strftime("%Y%m%d %H%M%S.%f")
            cv2.putText(
                B,
                date_str + " UTC",
                (10, B.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                255,
            )

            # The Hough Transform
            lines = cv2.HoughLinesP(
                accum_thresh,
                rho=shared.DETECT.LENGTH,
                theta=shared.DETECT.ANGLES,
                threshold=shared.DETECT.THRESHOLD,
                minLineLength=shared.DETECT.MINLINE,
                maxLineGap=shared.DETECT.LINESKIP,
            )
            # If we detect lines, draw a box around each one and initialize
            # or perpetuate recording
            if lines is not None and len(lines) < 50:
                # for eachline in lines:
                # for x1, y1, x2, y2 in eachline:
                # Bounding box edges multiplied by 2 to account for dimension
                # reduction earlier
                # drawBoundingHough(R, 2*x1, 2*x2, 2*y1, 2*y2)
                updateConsecFrames = False
                consecFrames = 0

                # If not already recording, start the recording!
                if not kcw.recording:
                    # Get the current free space on the disk in megabytes
                    free_space = shutil.disk_usage(savepath).free * 1e-6
                    # If we have more than 500MB available, go ahead and
                    # start the recording, else stop program
                    if free_space > 500:
                        # print("New event found at time: {}".format(date_str))
                        p = "{}/{}.avi".format(
                            savepath, date_num.strftime("%Y%m%d_%H%M%S")
                        )
                        # kcw.start(p, cv2.VideoWriter_fourcc(*'H264'), 30)
                        # kcw.start(p, cv2.VideoWriter_fourcc(*'FFV1'), 30)
                        kcw.start(p, cv2.VideoWriter_fourcc(*"XVID"), 30)
                        # kcw.start(p, cv2.VideoWriter_fourcc(*'HFYU'), 30)
                        d6log.info("New event detected. Video name: {}".format(p))
                        write_to_table(get_Hough_Avg_Pt(lines[0]))
                    else:
                        d6log.warning(
                            "Terminating observation run due to lack of storage"
                        )
                        disk_full = True
                        shared.ANALYZE_ON = False
                        finish_session(sessionid)

            # Create output image with grayscale image saved as blue color
            # output = cv2.merge([B, G, R])
            output = cv2.cvtColor(B, cv2.COLOR_GRAY2RGB)

            # Wrapping things up
            if updateConsecFrames:
                consecFrames += 1

            # Update buffer with latest frame
            kcw.update(output)

            # If too many frames w/o an event, stop recording
            if kcw.recording and consecFrames >= buffsize:
                if kcw.toolong:
                    d6log.info("Event was too long and was erased.")
                else:
                    d6log.info("Event completed and video recording finished")
                kcw.finish()

            # Show windows if desired
            if not headless:
                cv2.imshow("Output", output)
                # cv2.imshow("Timestamp",G)
                # cv2.imshow("Box", R)
                cv2.imshow("Background", avg)
                cv2.imshow("Subtracted", thresh)
                cv2.imshow("Accumulated", accum_thresh)

                key = cv2.waitKey(delay)

                # Exit script early. This does not work if running in headless mode
                if key == ord("q"):
                    shared.ANALYZE_ON = False
                    d6log.info("Analysis manually stopped!")

            framenum += 1
            endframetime = time.time()

            # Occasionally print out the current framerate
            if not framenum % 5:
                shared.FRAMERATE = 1 / (endframetime - startframetime)

            # Check time
            if shared.STARTTIME <= time.localtime().tm_hour < shared.ENDTIME:
                shared.ANALYZE_ON = False
                finish_session(sessionid)
                d6log.info("Day has come. Analysis going to sleep.")

            if not shared.RUNNING:
                break

        if kcw.recording:
            kcw.finish()

        # if key == ord("q"):
        # break

        if not shared.RUNNING:
            shared.ANALYZE_ON = False
            d6log.info("Analysis has been stopped manually.")
            finish_session(sessionid)
            break

        if disk_full:
            break

    d6log.info("Observing session finished.")


if __name__ == "__main__":
    shared.RUNNING = True
    grabbed = False
    shared.ANALYZE_ON = False
    gray = []
    shared.STARTTIME = 4
    shared.ENDTIME = 12

    # Construct the Argument Parser and Parse away!
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video", help="Path to desired video file")
    ap.add_argument(
        "-b",
        "--buffer-size",
        type=int,
        default=32,
        help="Buffer size of video clip writer (defaults to 32)",
    )
    ap.add_argument("-o", "--output", help="Path to desired output files")
    ap.add_argument(
        "-n",
        "--headless",
        action="store_true",
        help="Pass option to suppress monitoring output",
    )
    ap.add_argument(
        "-d",
        "--delay",
        type=int,
        default=1,
        help="Delay in playback of frames. Only use for saved videos",
    )
    args = vars(ap.parse_args())
    # print(args)

    # cProfile.run('main()')
    analyze(
        args["buffer_size"],
        args["output"],
        args["headless"],
        args["video"],
        args["delay"],
    )
