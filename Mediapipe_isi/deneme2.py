import cv2
import mediapipe as mp
import numpy as np
import math
import time
from collections import deque
import json

class FingerDrawingApp:
    def __init__(self):
        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.8,
            min_tracking_confidence=0.7,
            model_complexity=1
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Canvas ve çizim
        self.canvas = None
        self.drawing_points = []
        self.current_stroke = []
        self.is_drawing = False
        self.prev_point = None
        self.finger_history = deque(maxlen=10)
        self.smoothing_factor = 0.7
        self.min_movement = 5

        # Jest
        self.gesture_history = deque(maxlen=8)
        self.last_gesture_time = 0
        self.gesture_cooldown = 0.8

        # Yazı
        self.written_text = ""
        self.stats = {'characters_written': 0, 'strokes_drawn': 0, 'session_start': time.time()}

        # Renkler
        self.colors = {
            'draw': (0, 255, 100),
            'ui': (255, 255, 255),
            'highlight': (0, 255, 255),
            'success': (0, 255, 0),
            'error': (0, 0, 255),
            'background': (40, 40, 40)
        }
        self.brush_size = 3
        self.canvas_alpha = 0.3


    def get_finger_positions(self, landmarks, frame_shape):
        h, w = frame_shape[:2]
        points = {
            'wrist': 0, 'thumb_tip': 4, 'thumb_mcp': 2,
            'index_tip': 8, 'index_pip': 6, 'index_mcp': 5,
            'middle_tip': 12, 'middle_pip': 10,
            'ring_tip': 16, 'ring_pip': 14,
            'pinky_tip': 20, 'pinky_pip': 18
        }
        positions = {}
        for k, idx in points.items():
            positions[k] = (int(landmarks[idx].x * w), int(landmarks[idx].y * h))
        return positions

    def detect_gesture(self, positions):
        fingers_up = []
        thumb_up = positions['thumb_tip'][0] > positions['thumb_mcp'][0]
        fingers_up.append(thumb_up)
        for tip, pip in [('index_tip','index_pip'), ('middle_tip','middle_pip'), ('ring_tip','ring_pip'), ('pinky_tip','pinky_pip')]:
            fingers_up.append(positions[tip][1] < positions[pip][1])
        up_count = sum(fingers_up)
        if fingers_up == [False, True, False, False, False]: return "draw", 0.9
        elif fingers_up == [False, True, True, False, False]: return "peace", 0.8
        elif up_count == 0: return "fist", 0.9
        elif up_count >= 4: return "open", 0.7
        elif fingers_up == [True, False, False, False, False]: return "thumb", 0.8
        elif fingers_up == [False, False, False, False, True]: return "pinky", 0.7
        return "unknown", 0.3

    def smooth_point(self, point):
        self.finger_history.append(point)
        if len(self.finger_history) < 3: return point
        weights = np.linspace(0.1, 1.0, len(self.finger_history))
        weights /= weights.sum()
        points_arr = np.array(list(self.finger_history))
        smoothed = np.average(points_arr, axis=0, weights=weights)
        return tuple(map(int, smoothed))

    def distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def process_gesture_command(self, gesture, confidence):
        t = time.time()
        if confidence < 0.6 or t - self.last_gesture_time < self.gesture_cooldown: return
        if gesture == "peace":
            if self.canvas is not None: self.canvas.fill(0)
            self.drawing_points = []
            self.written_text = ""
            self.stats = {'characters_written': 0, 'strokes_drawn': 0, 'session_start': time.time()}
            print("🧹 Temizlendi!")
        elif gesture == "open":
            self.written_text += " "
            print("Boşluk eklendi")
        elif gesture == "thumb":
            self.written_text += "\n"
            print("Yeni satır eklendi")
        elif gesture == "pinky" and self.written_text:
            self.written_text = self.written_text[:-1]
            print("Geri al")
        self.last_gesture_time = t

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
        if self.canvas is None:
            ret, frame = cap.read()
            h,w = frame.shape[:2]
            self.canvas = np.zeros((h,w,3), dtype=np.uint8)

        while True:
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.flip(frame,1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)

            gesture, conf = "none",0
            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, lm, self.mp_hands.HAND_CONNECTIONS)
                    pos = self.get_finger_positions(lm.landmark, frame.shape)
                    gesture, conf = self.detect_gesture(pos)
                    if gesture == "draw" and conf>0.7:
                        pt = self.smooth_point(pos['index_tip'])
                        if not self.is_drawing:
                            self.is_drawing=True
                            self.current_stroke=[pt]
                            self.prev_point=pt
                        else:
                            if self.prev_point and self.distance(pt,self.prev_point)>=self.min_movement:
                                self.current_stroke.append(pt)
                                cv2.line(self.canvas, self.prev_point, pt, self.colors['draw'], self.brush_size)
                                self.prev_point=pt
                    elif gesture=="fist" and conf>0.7:
                        if self.is_drawing and len(self.current_stroke)>2:
                            self.drawing_points.append(self.current_stroke.copy())
                            self.written_text += "*"
                            self.stats['strokes_drawn']+=1
                            self.stats['characters_written']+=1
                            self.current_stroke=[]
                        self.is_drawing=False
                        self.prev_point=None
                    else:
                        self.process_gesture_command(gesture, conf)
                        self.is_drawing=False
                        self.prev_point=None

            # Overlay canvas
            overlay = cv2.addWeighted(frame,0.7,self.canvas,self.canvas_alpha,0)
            # Yazı göstergesi
            cv2.putText(overlay,f"Yazilan Metin: {self.written_text[-50:]}",(20,50),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2)
            cv2.imshow("Finger Drawing App", overlay)

            key=cv2.waitKey(1)&0xFF
            if key==ord('q'): break
            elif key==ord('s'):
                ts=int(time.time())
                cv2.imwrite(f"cizim_{ts}.png",self.canvas)
                with open(f"metin_{ts}.txt","w",encoding="utf-8") as f:
                    f.write(self.written_text)
                print(" Kaydedildi!")

        cap.release()
        cv2.destroyAllWindows()
        print("Çıkış yapıldı!")

if __name__=="__main__":
    app = FingerDrawingApp()
    app.run()
