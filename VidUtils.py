# Importing all the necessities
from collections import deque
from threading import Thread
from queue import Queue
import time
import os
import cv2


class KeyClipWriter:
    def __init__(self, bufSize=64, timeout=1.0):
        # Maximum number of frames to be kept in memory
        self.bufSize = bufSize
        # Sleep timeout for threading to prevent lock competition
        self.timeout = timeout

        # Initialize everything
        self.frames = deque(maxlen=bufSize)
        self.Q = None
        self.writer = None
        self.thread = None
        self.recording = False
        self.outputPath = None

    def update(self, frame):
        # Add frame to the frame buffer
        self.frames.appendleft(frame)

        # If we are also recording, add the frame to the write queue as well
        if self.recording:
            self.Q.put(frame)

    def start(self, outputPath, fourcc, fps):
        # Set recording flag
        self.recording = True
        self.outputPath = outputPath
        # Initialize writer
        self.writer = cv2.VideoWriter(
            outputPath,
            fourcc,
            fps,
            (self.frames[0].shape[1], self.frames[0].shape[0]),
            True,
        )
        # Initialize queue of frames to be written
        self.Q = Queue()

        # Add everything currently in the frames buffer to the queue
        for i in range(len(self.frames), 0, -1):
            self.Q.put(self.frames[i - 1])

        # Start a thread to write the frames
        self.thread = Thread(target=self.write, args=())
        self.thread.daemon = True
        self.thread.start()

    def write(self):
        # Start up the writing loop
        while True:
            # If done recording, exit thread
            if not self.recording:
                return

            # Are there frames in the queue?
            if not self.Q.empty():
                # Then grab the next frame and write it!
                frame = self.Q.get()
                self.writer.write(frame)
            # Otherwise, sleep for a moment to not interfere with the update process
            else:
                time.sleep(self.timeout)

    def flush(self):
        # Empty the queue by writing out the rest of what is in it
        time1 = time.time()
        while not self.Q.empty():
            frame = self.Q.get()
            self.writer.write(frame)
        time2 = time.time()
        # print("Flush elapsed time was: {}".format(time2-time1))

    def finish(self):
        # Set recording flag
        self.recording = False
        self.thread.join()
        self.flush()
        self.writer.release()

    def terminate(self):
        self.recording = False
        self.thread.join()
        self.writer.release()
        os.remove(self.outputPath)


class ShortClipWriter:
    """Class to better manage writing out video files on a running basis"""

    def __init__(self, bufSize=60, max_frames=200):
        # Maximum number of frames to be kept in memory
        self.bufSize = bufSize
        # Max number of frames for a "short clip"
        self.rec_max_frames = max_frames

        # Initialize everything
        self.frames = deque(maxlen=bufSize)
        self.Q = None
        self.writer = None
        self.threads = []
        self.recording = False
        self.outputPath = None
        self.toolong = False

    def update(self, frame):
        """Update both the rolling buffer and, if recording,
        update the video buffer as well. Takes a single np.array
        as a frame.
        """
        # Add frame to the frame buffer
        self.frames.append(frame)

        # If we are also recording, add the frame to the write queue as well
        if self.recording:
            # We only want short clips, so flag long recordings
            if len(self.Q) > self.rec_max_frames:
                self.toolong = True
            else:
                self.Q.append(frame)

    def start(self, outputPath, fourcc, fps):
        """Starts a video recording event, setting the output path and
        other video parameters. Adds the last buffer of images to the
        video buffer to be written to disk upon the events conclusion.

        outputPath: (str) file location of written video
        fourcc: (str) fourcc codec to be used
        fps: (int) number of desired frames per second of the video
        """
        # Set initial recording flags
        self.recording = True
        self.toolong = False
        self.outputPath = outputPath
        self.fourcc = fourcc
        self.fps = fps

        # Initialize queue of frames to be written
        self.Q = deque()

        # Add everything currently in the frames buffer to the queue
        self.Q.extend(self.frames)

    def write(self, framelist, outputPath, fourcc, fps):
        """Takes every frame in the provided framelist deque and writes
        to video, releasing the writer upon conclusion.

        framelist: (deque) Queue of np.array frames to be written to video
        """
        # Initialize writer
        writer = cv2.VideoWriter(
            outputPath,
            fourcc,
            fps,
            (framelist[0].shape[1], framelist[0].shape[0]),
            True,
        )
        while len(framelist) > 0:
            frame = framelist.popleft()
            writer.write(frame)
        writer.release()
        return

    def finish(self):
        """Upon conclusion of an event, stops the recording and sends
        the queue of frames to a separate thread to do the writing to
        disk.
        """
        # Set recording flag
        self.recording = False

        if not self.toolong:
            # Start a thread to write the frames
            self.threads.append(Thread(target=self.write, args=(self.Q.copy(), self.outputPath, self.fourcc, self.fps)))
            self.threads[-1].daemon = False
            self.threads[-1].start()


class VideoStream:
    def __init__(self, src=0):
        # Initialize and read first frame
        self.stream = cv2.VideoCapture(src)
        self.grabbed, self.frame = self.stream.read()
        # Stopping variable
        self.stopped = False
        self.Q = Queue()

    def start(self):
        # Start the thread to read from video stream
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        # Loop forever until stopped
        while True:
            # Break out if stopped
            if self.stopped:
                return

            # Else, read next frame from stream
            # self.grabbed, self.frame = self.stream.read()
            self.Q.put(self.stream.read()[1])
            # self.Q.put(self.frame)

    def read(self):
        # Return latest frame
        while True:
            if not self.Q.empty():
                return self.Q.get()

    def stop(self):
        # Indicate the thread should be stopped
        self.stopped = True
