from ultralytics import YOLO, settings

settings.update({"wandb": True})

def main():
    model = YOLO("yolov8n-pose.pt")
    model.train(
        data="badminton.yaml", 
        epochs=100,
        patience=20, # Arrête si pas d'amélioration pendant 20 epochs
        imgsz=640, 
        batch=8,
        device=0,
        workers=1,
        project="badminton_project",
        name="100_epochs",
        # Augmentations de données pour éviter l'overfitting
        degrees=10.0, # Rotation légère (très important si la caméra bouge)
        scale=0.5, # Zoom in/out (force à reconnaitre des terrains plus petits/grands)
        mosaic=1.0, # Mélange 4 images (excellent pour YOLO)
        hsv_h=0.015, # Variation de teinte
        hsv_s=0.4, # Variation de saturation (lumière changeante)
        hsv_v=0.4, # Variation de luminosité
        fliplr=0.5, # Miroir horizontal (le terrain est symétrique gauche/droite)
        flipud=0.0, # Pas de miroir vertical pour le badminton
                    # (le haut et le bas sont différents en perspective)
        save=True
    )

if __name__ == "__main__":
    main()