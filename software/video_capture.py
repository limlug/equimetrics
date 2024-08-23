import numpy as np
import cv2
import uuid
import sqlite3
from datetime import datetime
import cv2 as cv



conn = sqlite3.connect('sensors.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS videos
             (name TEXT, start_time TEXT, end_time TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS videos_sync
             (name TEXT, frame_count INTEGER, timestamp TEXT)''')
name = str(uuid.uuid4())
color_path = f'{name}_rgb.avi'
colorwriter = cv2.VideoWriter(color_path, cv2.VideoWriter_fourcc(*'XVID'), 30, (640, 480), 1) #cv2.VideoWriter_fourcc(*'XVID'), 30, (1280, 720), 1)
cap = cv.VideoCapture(4)
frame_interval = 3000  # Save data every 3000 frames
frame_count = 0
frame_global_count = 0

try:
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    while True:
        try:
            ret, frame = cap.read()

            # convert images to numpy arrays
            #color_image = np.asanyarray(frame.get_data())

            colorwriter.write(frame)
            frame_global_count += 1
            c.execute("INSERT INTO videos_sync VALUES (?, ?, ?)",
                          (name, frame_global_count, datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')))
            conn.commit()

        except KeyboardInterrupt:
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            c.execute("INSERT INTO videos VALUES (?, ?, ?)",
                      (name, start_time, end_time))
            conn.commit()
            break

finally:
    cap.release()
    colorwriter.release()
    conn.close()
