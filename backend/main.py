import cv2
import mediapipe as mp
import numpy as np
import base64
import webview
import threading
import math
import playlist_manager
import json

import time
# 1. Configurazione MediaPipe Tasks
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='hand_landmarker.task'),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=2
)
ultimo_frame_base64 = ""
ultimo_comando = ""
COOLDOWN = 1
ULTIMO_TEMPO_COMANDO =0          
CONNESSIONI_MANO = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Pollice
    (0, 5), (5, 6), (6, 7), (7, 8),         # Indice
    (5, 9), (9, 10), (10, 11), (11, 12),    # Medio
    (9, 13), (13, 14), (14, 15), (15, 16), # Anulare
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Mignolo e Palmo
]

stream = cv2.VideoCapture(0)
inizio_tenuta_pollice = None
inizio_tenuta_mignolo = None


is_pinch_attivo = False
y_inizio_pinch = 0.0
volume_inizio_pinch = 0.5
if not stream.isOpened():
    print("Errore: Impossibile aprire la webcam.")
    exit()

# Impostazione risoluzione desiderata
stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)


class ApiBridge:
  
    def ready(self):
        """Questa funzione verrà chiamata direttamente da React quando è pronto"""
        print("-> Ricevuto segnale di 'Pronto' da React! Invio la playlist...")
        
        playlist_per_js = []
        for brano in playlist_manager.file_playlist:
            audio_base64 = base64.b64encode(brano["dati"]).decode('utf-8')
            playlist_per_js.append({
                "name": brano["nome"],
                "artist": "Local File",
                "albumArt": "",
                "dati": audio_base64
            })
        
        return {
            "playlist": playlist_per_js,
            "currentIndex": playlist_manager.currentSong,
            "volume": playlist_manager.volume
        }
    def get_latest_frame(self):
        global ultimo_frame_base64
        return ultimo_frame_base64
    
    def get_command(self):
        global ultimo_comando
        cmd = ultimo_comando
        ultimo_comando = "" 
        return cmd   

api = ApiBridge()

def loop_vision():
    global api, ultimo_frame_base64, ultimo_comando, COOLDOWN, ULTIMO_TEMPO_COMANDO,inizio_tenuta_pollice,is_pinch_attivo,y_inizio_pinch,volume_inizio_pinch, inizio_tenuta_mignolo
    with HandLandmarker.create_from_options(options) as landmarker:
        while stream.isOpened():
            ret, frame = stream.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
            risultati = landmarker.detect_for_video(mp_image, timestamp_ms)
            
            hand_x, hand_y = None, None

            if risultati.hand_landmarks:
                # Prende le coordinate del dito indice (punto 8) della prima mano
                indice = risultati.hand_landmarks[0][8]
                
                # Scala le coordinate sulla dimensione della finestra (1280x720)
                hand_x = int(indice.x * 1280)
                hand_y = int(indice.y * 720)

                # Disegna lo scheletro sul frame
                for hand_landmarks in risultati.hand_landmarks:
                    punti_pixel = {}
                    for idx, lm in enumerate(hand_landmarks):
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        punti_pixel[idx] = (cx, cy)
                        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

                    for partenza, arrivo in CONNESSIONI_MANO:
                        if partenza in punti_pixel and arrivo in punti_pixel:
                            cv2.line(frame, punti_pixel[partenza], punti_pixel[arrivo], (0, 255, 0), 2)

            
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            ultimo_frame_base64 = jpg_as_text



        
            if risultati.hand_landmarks:
                #controllo pausa/play
                mano = risultati.hand_landmarks[0]
                polso = mano[0]
                punte_dita = [8, 12, 16, 20]  # Escludiamo il pollice da questo ciclo standard                
                mano_chiusa = True
                SOGLIA_CHIUSO = 0.30
                dita_aperte=[]
                for punta in punte_dita:
                    distanza = math.sqrt((mano[punta].x - polso.x) ** 2 + (mano[punta].y - polso.y) ** 2)
                    if distanza > SOGLIA_CHIUSO:
                        
                        dita_aperte.append(punta)
                        mano_chiusa = False

                # controllo skip/back                
                distanza_pollice = math.sqrt((mano[4].x - mano[17].x) ** 2 + (mano[4].y - mano[17].y) ** 2)
        
                SOGLIA_POLLICE = 0.20 
                can_skip = False
                if distanza_pollice > SOGLIA_POLLICE:
                    dita_aperte.append(4)
                    mano_chiusa = False
                    tempo_attuale_frame = time.time()
                    if inizio_tenuta_pollice is None:
                        inizio_tenuta_pollice = tempo_attuale_frame
                    elif tempo_attuale_frame - inizio_tenuta_pollice >= 2.0:  # 2 o 3 secondi di tenuta
                        can_skip = True
                else:
                    # Se l'utente abbassa il pollice, azzeriamo il timer di tenuta
                    inizio_tenuta_pollice = None

                distanza_mignolo = math.sqrt((mano[4].x - mano[20].x) ** 2 + (mano[4].y - mano[20].y) ** 2)
                SOGLIA_MIGNOLO = 0.20 
                can_prev = False
                if distanza_mignolo > SOGLIA_MIGNOLO:
                    mano_chiusa = False
                    tempo_attuale_frame = time.time()
                    if inizio_tenuta_mignolo is None:
                        inizio_tenuta_mignolo = tempo_attuale_frame
                    elif tempo_attuale_frame - inizio_tenuta_mignolo >= 2.0: 
                        can_prev = True
                else:
                    inizio_tenuta_mignolo = None
                punta_pollice = mano[4]
                punta_mignolo = mano[20]

                
                distanza_pinch = math.sqrt(
                        (mano[4].x - mano[8].x) ** 2 + 
                        (mano[4].y - mano[8].y) ** 2
                    )
                SOGLIA_PINCH = 0.05  
                    
                if distanza_pinch < SOGLIA_PINCH:
                    if not is_pinch_attivo:
                            is_pinch_attivo = True
                            y_inizio_pinch = mano[0].y
                            volume_inizio_pinch = getattr(playlist_manager, 'volume', 0.5)
                        
                      
                    spostamento_y = y_inizio_pinch - mano[0].y 
                        
                    nuovo_volume = volume_inizio_pinch + spostamento_y
                    nuovo_volume = max(0.0, min(1.0, nuovo_volume))
                        
                    playlist_manager.volume = nuovo_volume
                    ultimo_comando = f"VOL:{nuovo_volume}"
                        
                    print(f"🔊 Volume (Scorrimento): {int(nuovo_volume * 100)}%")                     
                else:
                        is_pinch_attivo = False
                                       
                        tempo_attuale = time.time()
                        if tempo_attuale - ULTIMO_TEMPO_COMANDO > COOLDOWN:

                            if mano_chiusa:
                                playlist_manager.isPlaying = False
                                ultimo_comando = "PAUSE"
                                ULTIMO_TEMPO_COMANDO = time.time()
                                print("-> Musica in PAUSA")
                            else:
                                if len(dita_aperte) == 1 and dita_aperte[0] == 20 and can_prev:
                                    ultimo_comando = "PREV"
                                    playlist_manager.prevSong()
                                    ULTIMO_TEMPO_COMANDO = time.time()
                                    inizio_tenuta_mignolo = None
                                    print("-> Ritorno a PREV")
                                
                                elif len(dita_aperte) == 1 and dita_aperte[0] == 4 and can_skip:
                                    ultimo_comando = "NEXT"
                                    playlist_manager.skipSong()
                                    ULTIMO_TEMPO_COMANDO = time.time()
                                    inizio_tenuta_pollice = None

                                    print("-> Acvanti a NEXT")
                                
                                    
                                else:
                                    playlist_manager.isPlaying = True
                                    ultimo_comando = "PLAY"
                                    ULTIMO_TEMPO_COMANDO = time.time()
                                    print("-> Musica in PLAY") 

                # controllo avanti/indietro

    stream.release()

if __name__ == '__main__':
    t = threading.Thread(target=loop_vision, daemon=True)
    t.start()

    window = webview.create_window(
        "Player Interattivo con Gesture",
        "http://localhost:5173",
        width=1280,
        height=720,
        resizable=True,
        js_api=api
    )

    webview.start(debug=True)