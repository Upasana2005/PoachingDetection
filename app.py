# app.py - Simple Web Interface
from flask import Flask, render_template, request, jsonify, send_file
from ultralytics import YOLO
import os
from werkzeug.utils import secure_filename
import cv2
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALERT_FOLDER'] = 'alerts'

os.makedirs('uploads', exist_ok=True)
os.makedirs('alerts', exist_ok=True)

# Load model
model_path = 'models/poaching_model/weights/best.pt'
model = YOLO(model_path) if os.path.exists(model_path) else None
class_names = ['animal', 'ranger', 'poacher', 'weapon']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return jsonify({'error': 'No file'})
    
    file = request.files['video']
    path = os.path.join('uploads', file.filename)
    file.save(path)
    
    # Process video
    cap = cv2.VideoCapture(path)
    alerts = []
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame_count += 1
        if frame_count % 30 != 0: continue
        
        results = model(frame)
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls in [2, 3]:  # poacher or weapon
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_path = f"alerts/{timestamp}.jpg"
                    cv2.imwrite(img_path, frame)
                    alerts.append({
                        'time': timestamp,
                        'type': class_names[cls],
                        'image': f'/alerts/{timestamp}.jpg'
                    })
    
    return jsonify({'alerts': alerts})

@app.route('/alerts/<filename>')
def get_alert(filename):
    return send_file(f'alerts/{filename}')

if __name__ == '__main__':
    app.run(debug=True)