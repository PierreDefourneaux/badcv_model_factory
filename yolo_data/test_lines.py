import cv2
from ultralytics import YOLO
import numpy as np


MODEL_PATH = 'badminton_project/100_epochs/weights/best.pt'
VIDEO_PATH = 'video_test1.mp4'
OUTPUT_PATH = 'video_result_100_epochs.mp4'
CONF_THRESHOLD = 0.5  # Ignore les points incertains



COURT_CONNECTIONS = [
    (0, 19), (19, 18), (16, 15), (15, 14), (18, 17), (17, 16), (1, 13), (2, 12),
    (3, 11), (4, 5), (5, 6), (6, 7), (8, 9), (9, 10), (6, 7), (7, 8), (0, 1), 
    (1, 2), (2, 3), (3, 4), (19, 5), (18, 6), (17, 7), (16, 8), (15, 9),    
    (14, 13), (13, 12), (12, 11), (11, 10)
]
NET_CONNECTIONS = [
    (20, 21), 
    (23, 22), 
    (20, 23), 
    (21, 22)  
]

def main():
    print(f"Chargement du modèle depuis {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Erreur: Impossible d'ouvrir {VIDEO_PATH}")
        return

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

    print(f"Traitement de la vidéo {width}x{height} à {fps} FPS...")

    frame_count = 0
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame_count += 1
        
        results = model(frame, conf=CONF_THRESHOLD, verbose=False)

        for r in results:
            if r.keypoints is not None and r.keypoints.xy.numel() > 0:
                # Récupérer les keypoints (x, y)
                kpts = r.keypoints.xy[0].cpu().numpy()
                
                # --- DESSIN DU TERRAIN (VERT) ---
                for p1_idx, p2_idx in COURT_CONNECTIONS:
                    # Vérifier que les points existent (pas [0,0])
                    if p1_idx < len(kpts) and p2_idx < len(kpts):
                        pt1 = tuple(map(int, kpts[p1_idx]))
                        pt2 = tuple(map(int, kpts[p2_idx]))
                        
                        if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                            cv2.line(frame, pt1, pt2, (0, 255, 0), 2, cv2.LINE_AA)

                # --- DESSIN DU FILET (ROUGE) ---
                for p1_idx, p2_idx in NET_CONNECTIONS:
                    if p1_idx < len(kpts) and p2_idx < len(kpts):
                        pt1 = tuple(map(int, kpts[p1_idx]))
                        pt2 = tuple(map(int, kpts[p2_idx]))
                        
                        if pt1[0] > 0 and pt1[1] > 0 and pt2[0] > 0 and pt2[1] > 0:
                            cv2.line(frame, pt1, pt2, (0, 0, 255), 3, cv2.LINE_AA)

                # --- DESSIN DES POINTS (OPTIONNEL, POUR DEBUG) ---
                for i, (x, y) in enumerate(kpts):
                    if x > 0 and y > 0:
                        color = (0, 0, 255) if i >= 20 else (0, 255, 255) # Rouge pour filet, Jaune pour terrain
                        cv2.circle(frame, (int(x), int(y)), 4, color, -1)

        # Enregistrement
        out.write(frame)
        
        # Affichage temps réel (appuyer sur 'q' pour quitter)
        cv2.imshow("Badminton Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Terminé ! Vidéo sauvegardée sous : {OUTPUT_PATH}")

if __name__ == "__main__":
    main()