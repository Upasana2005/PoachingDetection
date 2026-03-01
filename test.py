# test.py - Test your trained model
from ultralytics import YOLO
import cv2
import os

print("="*60)
print("TESTING POACHING DETECTION MODEL")
print("="*60)

# Step 1: Find model
print("\n🔍 Looking for trained model...")
model_path = 'runs/detect/models/poaching_model2/weights/best.pt'
if not os.path.exists(model_path):
    print("❌ Model not found! Train first.")
    exit()

# Step 2: Load model
print("📥 Loading model...")
model = YOLO(model_path)
class_names = ['animal', 'ranger', 'poacher', 'weapon']
print("✅ Model loaded!")

# Step 3: Ask what to test
print("\n" + "-"*40)
print("OPTIONS:")
print("1. Test on a single image")
print("2. Test on all images in folder")
choice = input("\nEnter choice (1 or 2): ")

if choice == '1':
    path = input("Enter image path: ")
    if os.path.exists(path):
        results = model(path)
        result_img = results[0].plot()
        cv2.imshow('Result', result_img)
        cv2.imwrite('test_result.jpg', result_img)
        print("✅ Result saved as test_result.jpg")
        cv2.waitKey(0)
    else:
        print("❌ File not found")

elif choice == '2':
    folder = input("Enter folder path: ")
    if os.path.exists(folder):
        os.makedirs('test_results', exist_ok=True)
        images = [f for f in os.listdir(folder) 
                 if f.endswith(('.jpg','.png','.jpeg'))]
        for i, img in enumerate(images[:5]):
            print(f"Testing {i+1}/{len(images[:5])}")
            results = model(os.path.join(folder, img))
            cv2.imwrite(f'test_results/result_{i}.jpg', results[0].plot())
        print("✅ Results in 'test_results' folder")