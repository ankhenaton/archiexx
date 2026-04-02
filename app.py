import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import google.generativeai as genai
import PyPDF2

app = Flask(__name__)
app.config['SECRET_KEY'] = '12Demir04Maviserit2021X1' # Güvenlik için değiştirin
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///archie.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # Max 50 MB

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- VERİTABANI MODELLERİ ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gemini_api_key = db.Column(db.String(255), nullable=True)

class ArchiveFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ai_summary = db.Column(db.Text, nullable=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(50), default='#ffffff') # Material design renk kodları için

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    attached_file = db.Column(db.String(255), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROTALAR (ROUTES) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Sadece senin istediğin kullanıcı adı ve şifre
        if username == 'serkanmaviseri' and password == '12Demir04Maviserit2021':
            user = User.query.filter_by(username='serkanmaviseri').first()
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Hatalı giriş!')
    return render_template('login.html')

@app.route('/')
@login_required
def dashboard():
    notes = Note.query.all()
    reminders = Reminder.query.all()
    return render_template('dashboard.html', notes=notes, reminders=reminders)

@app.route('/archive', methods=['GET', 'POST'])
@login_required
def archive():
    if request.method == 'POST':
        files = request.files.getlist('files')
        description = request.form.get('description')
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                new_file = ArchiveFile(filename=filename, description=description)
                db.session.add(new_file)
        db.session.commit()
        flash('Dosyalar başarıyla yüklendi.')
        return redirect(url_for('archive'))
    
    files = ArchiveFile.query.all()
    return render_template('archive.html', files=files)

@app.route('/ai_summarize/<int:file_id>', methods=['POST'])
@login_required
def ai_summarize(file_id):
    file_record = ArchiveFile.query.get_or_404(file_id)
    settings = Setting.query.first()
    
    if not settings or not settings.gemini_api_key:
        flash('Admin panelinden Gemini API anahtarını ayarlamalısınız.', 'error')
        return redirect(url_for('archive'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)
    
    # Basit PDF Metin Çıkarma Örneği (AI için metni hazırlama)
    extracted_text = ""
    if filepath.endswith('.pdf'):
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted_text += page.extract_text()
    
    # Gemini 1.5 Flash Entegrasyonu
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Lütfen aşağıdaki metni detaylı ama özlü bir şekilde özetle:\n\n{extracted_text[:10000]}" # İlk 10 bin karakter
        response = model.generate_content(prompt)
        
        file_record.ai_summary = response.text
        db.session.commit()
        flash('Yapay Zeka özeti başarıyla oluşturuldu.')
    except Exception as e:
        flash(f'AI Hatası: {str(e)}', 'error')

    return redirect(url_for('archive'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    setting = Setting.query.first()
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        if setting:
            setting.gemini_api_key = api_key
        else:
            new_setting = Setting(gemini_api_key=api_key)
            db.session.add(new_setting)
        db.session.commit()
        flash('Ayarlar kaydedildi.')
        return redirect(url_for('admin'))
    return render_template('admin.html', setting=setting)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # İlk kurulumda kullanıcıyı ve klasörü oluştur
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        if not User.query.filter_by(username='serkanmaviseri').first():
            user = User(username='serkanmaviseri', password='12Demir04Maviserit2021')
            db.session.add(user)
            db.session.commit()
    # Geliştirme ortamı için. Canlıda Gunicorn kullanılacak.
    app.run(debug=True, host='0.0.0.0', port=5000)