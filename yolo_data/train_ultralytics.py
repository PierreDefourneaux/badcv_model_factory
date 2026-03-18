from ultralytics import YOLO, settings

settings.update({"wandb": True})

def main():
    model = YOLO("yolov8n-pose.pt")
    model.train(
        data="badminton.yaml", 
        epochs=10,
        patience=20,
        imgsz=640, 
        batch=8,
        device=0,
        workers=1,
        project="badminton_project",
        name="test_monitoring_v3",
        degrees=10.0,
        scale=0.5,
        mosaic=1.0,
        hsv_h=0.015,
        hsv_s=0.4,
        hsv_v=0.4,
        fliplr=0.5,
        flipud=0.0,
        save=True
    )

if __name__ == "__main__":
    main()