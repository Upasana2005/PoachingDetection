# app.py - Complete Flask Application with Authentication
from flask_mail import Mail, Message
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
import cv2
from ultralytics import YOLO
from werkzeug.utils import secure_filename
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALERT_FOLDER'] = 'alerts'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}

# Email Configuration - REPLACE WITH YOUR EMAIL
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # CHANGE THIS
app.config['MAIL_PASSWORD'] = 'your-app-password'     # CHANGE THIS
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'  # CHANGE THIS

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ALERT_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page'

# Load AI Model - UPDATE THIS PATH TO YOUR MODEL
MODEL_PATH = 'runs/detect/models/poaching_model2/weights/best.pt'  # CHANGE IF NEEDED
model = None
if os.path.exists(MODEL_PATH):
    try:
        model = YOLO(MODEL_PATH)
        print(f"✅ Model loaded from {MODEL_PATH}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
else:
    print(f"❌ Model not found at {MODEL_PATH}")
    print("   Please update MODEL_PATH variable")

# ========== DATABASE MODELS ==========
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    alerts = db.relationship('Alert', backref='user', lazy=True)
    
    def get_id(self):
        return str(self.id)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    detection_type = db.Column(db.String(50))  # poacher or weapon
    confidence = db.Column(db.Float)
    video_name = db.Column(db.String(200))
    location = db.Column(db.String(200))  # Optional GPS data

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== HELPER FUNCTIONS ==========
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ========== EMAIL ALERT FUNCTION ==========
def send_alert_email(user_email, alert_data):
    """Send email alert when poacher/weapon detected"""
    try:
        # For testing without actual email - just print
        print("\n" + "="*50)
        print("📧 EMAIL ALERT WOULD BE SENT:")
        print(f"   To: {user_email}")
        print(f"   Subject: 🚨 POACHING ALERT - {alert_data['detection_type'].upper()} DETECTED")
        print(f"   Detection: {alert_data['detection_type']}")
        print(f"   Time: {alert_data['timestamp']}")
        print(f"   Confidence: {alert_data['confidence']}%")
        print(f"   Video: {alert_data['video_name']}")
        print("="*50 + "\n")
        
        # UNCOMMENT BELOW TO ACTUALLY SEND EMAILS (requires Gmail setup)
        """
        msg = Message(
            subject=f"🚨 POACHING ALERT - {alert_data['detection_type'].upper()} DETECTED",
            recipients=[user_email],
            html=f"<h2>🚨 CRITICAL ALERT</h2><p><strong>{alert_data['detection_type'].upper()} DETECTED!</strong></p><p>Time: {alert_data['timestamp']}</p><p>Confidence: {alert_data['confidence']}%</p><p>Video: {alert_data['video_name']}</p><p><a href='http://127.0.0.1:5000/alerts'>View Alert</a></p>"
        )
        mail.send(msg)
        """
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ========== LANDING PAGES ==========
@app.route('/')
def index():
    return render_template('main/index.html')

@app.route('/features')
def features():
    return render_template('main/features.html')

@app.route('/about')
def about():
    return render_template('main/about.html')

# ========== AUTHENTICATION ROUTES ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        company = request.form.get('company')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('signup'))
        
        # Hash password and create user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password, company=company)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created! Please login', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/signup.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot-password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# ========== DASHBOARD ROUTES ==========
@app.route('/dashboard')
@login_required
def dashboard():
    recent_alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.timestamp.desc()).limit(5).all()
    stats = {
        'total_alerts': Alert.query.filter_by(user_id=current_user.id).count(),
        'poacher_alerts': Alert.query.filter_by(user_id=current_user.id, detection_type='poacher').count(),
        'weapon_alerts': Alert.query.filter_by(user_id=current_user.id, detection_type='weapon').count(),
        'recent_count': len(recent_alerts)
    }
    return render_template('dashboard/dashboard.html', stats=stats, recent_alerts=recent_alerts)

@app.route('/upload')
@login_required
def upload_page():
    return render_template('dashboard/upload.html')

@app.route('/upload-video', methods=['POST'])
@login_required
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed = {'mp4', 'avi', 'mov', 'mkv'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Save video
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{current_user.id}_{timestamp}_{filename}"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(video_path)
        
        # ========== REAL DETECTION CODE ==========
        alerts_added = 0
        if model is not None:
            try:
                # Open video
                cap = cv2.VideoCapture(video_path)
                frame_count = 0
                alert_list = []  # Store alerts for email
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_count += 1
                    # Process every 30th frame to save time
                    if frame_count % 30 != 0:
                        continue
                    
                    # Run detection
                    results = model(frame)
                    
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                cls = int(box.cls[0])
                                conf = float(box.conf[0])
                                
                                # Alert for poacher (2) or weapon (3)
                                if cls in [2, 3]:
                                    alert_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    alert_filename = f"alert_{alert_time}_{current_user.id}_{alerts_added}.jpg"
                                    alert_path = os.path.join('alerts', alert_filename)
                                    
                                    # Draw bounding box on frame
                                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                                    color = (0, 0, 255) if cls == 2 else (255, 0, 0)
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                                    label = "POACHER" if cls == 2 else "WEAPON"
                                    cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10), 
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                    
                                    # Save frame
                                    cv2.imwrite(alert_path, frame)
                                    
                                    # Save to database
                                    new_alert = Alert(
                                        user_id=current_user.id,
                                        filename=alert_filename,
                                        detection_type='poacher' if cls == 2 else 'weapon',
                                        confidence=round(conf * 100, 1),
                                        video_name=unique_filename
                                    )
                                    db.session.add(new_alert)
                                    alert_list.append(new_alert)
                                    alerts_added += 1
                
                cap.release()
                db.session.commit()
                print(f"✅ Video processing complete. Found {alerts_added} alerts.")
                
                # Send email for each alert
                for alert in alert_list:
                    alert_data = {
                        'detection_type': alert.detection_type,
                        'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'confidence': alert.confidence,
                        'video_name': alert.video_name
                    }
                    send_alert_email(current_user.email, alert_data)
                
            except Exception as e:
                print(f"❌ Detection error: {str(e)}")
                db.session.rollback()
        else:
            print("⚠️ Model not loaded - skipping detection")
        # ========== END OF DETECTION CODE ==========
        
        # Return JSON
        return jsonify({
            'success': True,
            'message': f'Video uploaded successfully. Found {alerts_added} alerts.',
            'video': unique_filename,
            'alerts_found': alerts_added,
            'redirect': '/alerts'
        })
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/alerts')
@login_required
def alerts_page():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.timestamp.desc()).paginate(page=page, per_page=per_page)
    return render_template('dashboard/alerts.html', alerts=alerts)

@app.route('/api/alerts')
@login_required
def get_alerts():
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.timestamp.desc()).limit(10).all()
    return jsonify([{
        'id': a.id,
        'filename': a.filename,
        'timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'type': a.detection_type,
        'confidence': a.confidence,
        'video': a.video_name
    } for a in alerts])

@app.route('/settings')
@login_required
def settings_page():
    return render_template('dashboard/settings.html')

@app.route('/update-settings', methods=['POST'])
@login_required
def update_settings():
    user = current_user
    user.company = request.form.get('company', user.company)
    db.session.commit()
    flash('Settings updated successfully', 'success')
    return redirect(url_for('settings_page'))

# ========== API ENDPOINTS ==========
@app.route('/api/status')
def api_status():
    return jsonify({
        'model_loaded': model is not None,
        'status': 'online',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("\n" + "="*60)
    print("🚀 ECOEYE AI SYSTEM STARTED")
    print("="*60)
    print(f"📁 Model path: {MODEL_PATH}")
    print(f"✅ Model loaded: {model is not None}")
    if model is None:
        print("⚠️  WARNING: Model not loaded! Detection will not work.")
        print("   Please check your model path and run detection test.")
    print(f"📊 Detecting: poacher (ID 2), weapon (ID 3)")
    print(f"🌐 Open browser to: http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)