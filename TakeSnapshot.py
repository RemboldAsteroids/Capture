"""
Script to take snapshots of a specified duration.
No graphical output.
"""

import argparse
import cv2
import time
import numpy as np

class Snapshot:
    """Class to facilitate taking a simple snapshot of some determined exposure."""

    def __init__(self, output, exp, src):
        """
        Initialize class

        Args:
            output (str): File directory location of saved output
            exp (float): Duration of desired exposure
            src (int): Video source of camera to use
        """
        self.location = output
        self.exposure = exp
        self.src = src
        self.image = None

        self.cam = cv2.VideoCapture(self.src)
        self.start = time.time()
        self.expose()
        cv2.imwrite("{path}/Manual_{fname}.png".format(path=self.location, fname=time.strftime('%Y%m%d_%H%M%S')), self.image)

    def expose(self):
        """
        Gather frames from camera and stack (add) them until the
        desired exposure time is reached. Then normalize, stretch,
        and convert back to int8.

        Arguments:
            None
        Outputs:
            None
        """
        while time.time() - self.start < self.exposure:
            grabbed, frame = self.cam.read()
            if grabbed:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                frame = frame.astype(np.int32)
                if self.image is None:
                    self.image = frame
                else:
                    self.image += frame
        # Stretch image
        normalize = self.image / np.max(self.image)
        # Set back to int8
        self.image = (normalize * 255).astype(np.uint8)


def read_arguments():
    """
    Convenience function to setup and return argparse variables
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--output', help='Location to save snapshot', type=str)
    ap.add_argument('-e', '--exp', help='Duration (in seconds) to exposure and stack snapshot', type=float, default=1.0)
    ap.add_argument('-s', '--src', help='Video source number', type=int, default=0)
    args = vars(ap.parse_args())
    return args

if __name__ == '__main__':
    Snapshot(**read_arguments())
