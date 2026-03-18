## Pour entraîner le modèle :
```bash
cd /home/pierre/badCV_model_factory/yolo_data
uv run train_utraltics.py
```

Pour suivre le monitoring dans **Wandb.ia** : `ctrl+clic gauche` sur l'url qui apparait dans le terminal

## Pour tester le modèle :
Spécifier le chemin du modèle dans la ligne 6 de `test_lines.py` :
```python
MODEL_PATH = 'badminton_project/100_epochs/weights/best.pt'
```

```bash
cd /home/pierre/badCV_model_factory/yolo_data
uv test_lines.py
```
