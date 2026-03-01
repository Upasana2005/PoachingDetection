# train.py - Complete Training Script
import zipfile
import os
import yaml
from ultralytics import YOLO
import torch
import shutil

print("="*60)
print("TRAINING POACHING DETECTION MODEL")
print("="*60)

# Step 1: Check for dataset
print("\n📦 Looking for dataset.zip...")
if not os.path.exists("dataset.zip"):
    print("❌ ERROR: dataset.zip not found!")
    exit()

# Step 2: Extract
print("📂 Extracting dataset...")
if os.path.exists("dataset"):
    shutil.rmtree("dataset")
with zipfile.ZipFile("dataset.zip", 'r') as zip_ref:
    zip_ref.extractall("dataset")

# Step 3: Find data.yaml
print("🔍 Finding data.yaml...")
yaml_path = None
for root, dirs, files in os.walk("dataset"):
    if "data.yaml" in files:
        yaml_path = os.path.join(root, "data.yaml")
        break

if yaml_path is None:
    print("❌ data.yaml not found!")
    exit()

print(f"✅ Found at: {yaml_path}")

# Step 4: Show classes
with open(yaml_path, 'r') as f:
    data = yaml.safe_load(f)
print(f"\n📊 Classes: {data['names']}")

# Step 5: Check GPU
print("\n💻 Checking hardware...")
if torch.cuda.is_available():
    print("✅ GPU available - training fast!")
    device = 0
else:
    print("⚠️ No GPU - training slow")
    device = 'cpu'

# Step 6: Train
print("\n🚀 Starting training (1-3 hours)...")
model = YOLO('yolov8n.pt')
model.train(
    data=yaml_path,
    epochs=50,
    imgsz=640,
    batch=16,
    device=device,
    project='models',
    name='poaching_model'
)

print("\n✅✅ TRAINING COMPLETE!")
print("\n📁 Model saved at: models/poaching_model/weights/best.pt")
print("\n🔍 Class IDs for alerts:")
print("   0 = animal  → NO ALERT")
print("   1 = ranger  → NO ALERT")
print("   2 = poacher → 🚨 ALERT")
print("   3 = weapon  → 🚨 ALERT")