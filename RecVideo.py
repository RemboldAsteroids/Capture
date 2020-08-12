"""
Simple script to capture video to a timestamped
file. Starts when the script is run and terminates
when the 'q' key is pressed. Writes a timestamp to
the bottom of the video as well.
"""

import cv2
import numpy as np
from datetime import datetime as dt
from VidUtils import KeyClipWriter

vid = cv2.VideoCapture(2)
kcw = KeyClipWriter()

init_time = dt.strftime(dt.now(), "%Y%m%d_%H%M%S")
fname = f'/home/jedediah/Videos/AllSky/{init_time}.avi'
fwidth = int(vid.get(3))
fheight = int(vid.get(4))
fourcc = cv2.VideoWriter_fourcc(*'XVID')
# out = cv2.VideoWriter(fname, fourcc, 30.0, (fwidth, fheight), False)

count = 1
start = dt.now()
while True:
    ret, frame = vid.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    cv2.putText(gray, dt.now().strftime('%Y%m%d_%H%M%S.%f'),
            (10, gray.shape[0]-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (255,255,255)
            )
    kcw.update(gray)
    if not kcw.recording:
        kcw.start(fname, fourcc, 30)
    # out.write(gray)
    cv2.imshow('Display', gray)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    count += 1

end = dt.now()
print(f'FPS were {count/((end-start).total_seconds())}')
if kcw.recording:
    kcw.finish()
