import mediapipe as mp
import cv2
import numpy as np
import tempfile
import os
import math
import time
from collections import deque

class AdvancedHandDrawing:
    def __init__(self,
                 static_image_mode=False,
                 max_num_hands=2,
                 min_detection_confidence=0.7,
                 min_tracking_confidence=0.7):

        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_hands = mp.solutions.hands

        # .binarypb hatasını atlatmak için custom temp graph yoksa normal yolla patlarsın 
        graph_str = f"""
        input_stream: "input_video"
        output_stream: "multi_hand_landmarks"
        output_stream: "multi_handedness"
        node {{
          calculator: "FlowLimiterCalculator"
          input_stream: "input_video"
          input_stream: "FINISHED:multi_hand_landmarks"
          input_stream_info: {{
            tag_index: "FINISHED"
            back_edge: true
          }}
          output_stream: "throttled_input_video"
        }}
        node {{
          calculator: "PalmDetectionCalculator"
          input_stream: "IMAGE:throttled_input_video"
          output_stream: "DETECTIONS:palm_detections"
        }}
        node {{
          calculator: "HandLandmarkCpu"
          input_stream: "IMAGE:throttled_input_video"
          input_stream: "DETECTIONS:palm_detections"
          output_stream: "LANDMARKS:multi_hand_landmarks"
          output_stream: "HANDEDNESS:multi_handedness"
        }}
        """

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pbtxt")
        tmp_file.write(graph_str.encode("utf-8"))
        tmp_file.close()

        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        os.remove(tmp_file.name)

        # Çizim için değişkenler
        self.drawing_canvas = None
        self.prev_x, self.prev_y = None, None
        self.drawing_mode = False
        self.current_color = (0, 255, 0)  # Yeşil
        self.brush_thickness = 5
        self.eraser_mode = False
        
        # Renk paleti
        self.colors = {
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'red': (0, 0, 255),
            'yellow': (0, 255, 255),
            'purple': (255, 0, 255),
            'cyan': (255, 255, 0),
            'white': (255, 255, 255),
            'black': (0, 0, 0)
        }
        
        
        self.gesture_buffer = deque(maxlen=10)
        self.last_gesture_time = time.time()
        
        
        self.finger_positions = deque(maxlen=5)
        
        # UI elementleri
        self.show_ui = True
        self.ui_alpha = 0.7

    def process_frame(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image_rgb)
        return results

    def calculate_distance(self, point1, point2):
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def get_finger_positions(self, landmarks, image_shape):
        h, w = image_shape[:2]
        positions = {}
        
        # Parmak uçları landmark indeksleri
        finger_tips = {
            'thumb': 4,
            'index': 8,
            'middle': 12,
            'ring': 16,
            'pinky': 20
        }
        
        # Parmak diplerinin landmark indeksleri
        finger_bases = {
            'thumb': 3,
            'index': 6,
            'middle': 10,
            'ring': 14,
            'pinky': 18
        }
        
        for finger, tip_idx in finger_tips.items():
            tip = landmarks.landmark[tip_idx]
            base = landmarks.landmark[finger_bases[finger]]
            
            positions[finger] = {
                'tip': (int(tip.x * w), int(tip.y * h)),
                'base': (int(base.x * w), int(base.y * h)),
                'extended': tip.y < base.y if finger != 'thumb' else tip.x > base.x
            }
        
        return positions

    def detect_gesture(self, finger_positions):
        # Hangi parmaklar açık(daha geliştirilebilir)
        extended_fingers = [finger for finger, data in finger_positions.items() if data['extended']]
        
        
        if len(extended_fingers) == 1 and 'index' in extended_fingers:
            return 'draw'
        elif len(extended_fingers) == 2 and 'index' in extended_fingers and 'thumb' in extended_fingers:
            
            thumb_tip = finger_positions['thumb']['tip']
            index_tip = finger_positions['index']['tip']
            distance = self.calculate_distance(thumb_tip, index_tip)
            if distance < 40:
                return 'pinch_draw'
            else:
                return 'stop'
        elif len(extended_fingers) == 2 and 'index' in extended_fingers and 'middle' in extended_fingers:
            return 'erase'
        elif len(extended_fingers) == 3 and 'index' in extended_fingers and 'middle' in extended_fingers and 'ring' in extended_fingers:
            return 'color_change'
        elif len(extended_fingers) == 5:
            return 'clear_canvas'
        elif len(extended_fingers) == 0:
            return 'fist'
        else:
            return 'stop'

    def smooth_position(self, new_pos):
        self.finger_positions.append(new_pos)
        if len(self.finger_positions) < 3:
            return new_pos
        
        # Ortalama pozisyon hesapla
        avg_x = sum(pos[0] for pos in self.finger_positions) // len(self.finger_positions)
        avg_y = sum(pos[1] for pos in self.finger_positions) // len(self.finger_positions)
        return (avg_x, avg_y)

    def change_color_based_on_position(self, finger_tip, image_shape):
        h, w = image_shape[:2]
        x, y = finger_tip
        
        
        if x < w // 4:
            self.current_color = self.colors['red']
        elif x < w // 2:
            self.current_color = self.colors['green']
        elif x < 3 * w // 4:
            self.current_color = self.colors['blue']
        else:
            self.current_color = self.colors['yellow']

    def adjust_brush_thickness(self, hand_landmarks, image_shape):
        # El büyüklüğüne göre fırça kalınlığını ayarla
        h, w = image_shape[:2]
        
       
        wrist = hand_landmarks.landmark[0]
        middle_tip = hand_landmarks.landmark[12]
        
        wrist_pos = (int(wrist.x * w), int(wrist.y * h))
        middle_pos = (int(middle_tip.x * w), int(middle_tip.y * h))
        
        hand_size = self.calculate_distance(wrist_pos, middle_pos)
        
        # Kalınlığı 2-20 piksel arasında ayarla(opsiyonel)
        self.brush_thickness = max(2, min(20, int(hand_size / 10)))

    def draw_ui(self, image):
        if not self.show_ui:
            return
        
        h, w = image.shape[:2]
        overlay = image.copy()
        
        # Renk paleti
        color_names = ['red', 'green', 'blue', 'yellow', 'purple', 'cyan', 'white', 'black']
        for i, color_name in enumerate(color_names):
            x = 20 + i * 60
            y = 20
            color = self.colors[color_name]
            cv2.rectangle(overlay, (x, y), (x + 50, y + 30), color, -1)
            if color == self.current_color:
                cv2.rectangle(overlay, (x-2, y-2), (x + 52, y + 32), (255, 255, 255), 2)
        
        # Mod göstergesi
        mode_text = "ÇIZIM" if self.drawing_mode else "DURDUR"
        if self.eraser_mode:
            mode_text = "SİLGİ"
        
        cv2.putText(overlay, mode_text, (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Fırça kalınlığı
        cv2.putText(overlay, f"Kalinlik: {self.brush_thickness}", (20, h - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
       
        help_texts = [
            "1 parmak: Ciz",
            "2 parmak (V): Silgi",
            "3 parmak: Renk degistir",
            "5 parmak: Temizle",
            "Yumruk: Durdur"
        ]
        
        for i, text in enumerate(help_texts):
            cv2.putText(overlay, text, (w - 250, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Overlay'i ana görüntüye karıştır
        cv2.addWeighted(overlay, self.ui_alpha, image, 1 - self.ui_alpha, 0, image)

    def process_drawing(self, image, results):
        h, w = image.shape[:2]
        
        # Canvas oluştur
        if self.drawing_canvas is None:
            self.drawing_canvas = np.zeros((h, w, 3), dtype=np.uint8)
        
        current_time = time.time()
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Parmak pozisyonlarını al
                finger_positions = self.get_finger_positions(hand_landmarks, image.shape)
                
                # Gesture tanı
                gesture = self.detect_gesture(finger_positions)
                self.gesture_buffer.append(gesture)
                
                # Fırça kalınlığını ayarla
                self.adjust_brush_thickness(hand_landmarks, image.shape)
                
                # En yaygın gesture'ı kullan (stabilite için yoksa çok saçmalıyor)
                if len(self.gesture_buffer) >= 5:
                    most_common_gesture = max(set(self.gesture_buffer), key=self.gesture_buffer.count)
                else:
                    most_common_gesture = gesture
                
                # Index finger pozisyonu
                index_tip = finger_positions['index']['tip']
                smooth_tip = self.smooth_position(index_tip)
                
                # Gesture işlemleri
                if most_common_gesture == 'draw' or most_common_gesture == 'pinch_draw':
                    self.drawing_mode = True
                    self.eraser_mode = False
                    
                    if self.prev_x is not None and self.prev_y is not None:
                        cv2.line(self.drawing_canvas, (self.prev_x, self.prev_y), smooth_tip, 
                                self.current_color, self.brush_thickness)
                    
                    self.prev_x, self.prev_y = smooth_tip
                    
                elif most_common_gesture == 'erase':
                    self.drawing_mode = True
                    self.eraser_mode = True
                    
                    if self.prev_x is not None and self.prev_y is not None:
                        cv2.circle(self.drawing_canvas, smooth_tip, self.brush_thickness * 2, (0, 0, 0), -1)
                    
                    self.prev_x, self.prev_y = smooth_tip
                    
                elif most_common_gesture == 'color_change':
                    if current_time - self.last_gesture_time > 1.0:  # 1 saniye cooldown
                        self.change_color_based_on_position(smooth_tip, image.shape)
                        self.last_gesture_time = current_time
                    self.drawing_mode = False
                    self.prev_x, self.prev_y = None, None
                    
                elif most_common_gesture == 'clear_canvas':
                    if current_time - self.last_gesture_time > 2.0:  # 2 saniye cooldown
                        self.drawing_canvas = np.zeros((h, w, 3), dtype=np.uint8)
                        self.last_gesture_time = current_time
                    self.drawing_mode = False
                    self.prev_x, self.prev_y = None, None
                    
                else:
                    self.drawing_mode = False
                    self.eraser_mode = False
                    self.prev_x, self.prev_y = None, None
                
                # El çizgilerini göster
                if self.show_ui:
                    self.mp_drawing.draw_landmarks(
                        image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing_styles.get_default_hand_landmarks_style(),
                        self.mp_drawing_styles.get_default_hand_connections_style())
                
                # Aktif parmagı vurgula
                if self.drawing_mode:
                    cv2.circle(image, smooth_tip, 10, self.current_color, -1)
                    cv2.circle(image, smooth_tip, 12, (255, 255, 255), 2)
        else:
            self.drawing_mode = False
            self.prev_x, self.prev_y = None, None
        
        # Canvası ana görntüye ekle
        mask = cv2.cvtColor(self.drawing_canvas, cv2.COLOR_BGR2GRAY)
        mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)[1]
        mask_inv = cv2.bitwise_not(mask)
        
        image_bg = cv2.bitwise_and(image, image, mask=mask_inv)
        canvas_fg = cv2.bitwise_and(self.drawing_canvas, self.drawing_canvas, mask=mask)
        
        result = cv2.add(image_bg, canvas_fg)
        
        return result

def run_advanced_drawing():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    advanced_hands = AdvancedHandDrawing()
    
    print("=== GELİŞMİŞ EL ÇİZİM SİSTEMİ ===")
    print("Kontroller:")
    print("- 1 parmak (işaret): Çizim yap")
    print("- 2 parmak (V işareti): Silgi modu")
    print("- 3 parmak: Renk değiştir (ekran bölgesine göre)")
    print("- 5 parmak (açık el): Canvas'ı temizle")
    print("- Yumruk: Çizimi durdur")
    print("- 'u' tuşu: UI'yi aç/kapat")
    print("- 's' tuşu: Çizimi kaydet")
    print("- ESC: Çıkış")
    print("=" * 40)

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Kamera okunamıyor...")
            break

        image = cv2.flip(image, 1)
        results = advanced_hands.process_frame(image)
        
        # Çizim işlemlerini yap
        image = advanced_hands.process_drawing(image, results)
        
        # UI çiz
        advanced_hands.draw_ui(image)
        
        cv2.imshow('Gelişmiş El Çizim Sistemi', image)
        
        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC
            break
        elif key == ord('u'):  # UI toggle
            advanced_hands.show_ui = not advanced_hands.show_ui
        elif key == ord('s'):  # Save
            if advanced_hands.drawing_canvas is not None:
                timestamp = int(time.time())
                filename = f"drawing_{timestamp}.png"
                cv2.imwrite(filename, advanced_hands.drawing_canvas)
                print(f"Çizim kaydedildi: {filename}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_advanced_drawing()
