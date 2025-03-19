from flask import Flask, render_template, request, send_file, url_for, redirect, flash
import os
import uuid
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import zipfile
import io
import shutil

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 16MB max upload size

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('没有选择文件')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # 创建唯一的工作目录
        unique_id = str(uuid.uuid4())
        work_dir = os.path.join(app.config['UPLOAD_FOLDER'], unique_id)
        os.makedirs(work_dir, exist_ok=True)
        
        # 保存上传的PDF文件
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(work_dir, filename)
        file.save(pdf_path)
        
        # 转换PDF为图片
        try:
            images_folder = os.path.join(work_dir, 'images')
            os.makedirs(images_folder, exist_ok=True)
            
            # 使用pdf2image转换PDF为图片
            images = convert_from_path(pdf_path)
            
            # 保存每一页为单独的图片
            image_paths = []
            for i, image in enumerate(images):
                image_path = os.path.join(images_folder, f'page_{i+1}.png')
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
            
            # 创建包含所有图片的ZIP文件
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                for i, image_path in enumerate(image_paths):
                    zf.write(image_path, f'page_{i+1}.png')
            
            memory_file.seek(0)
            
            # 清理临时文件
            shutil.rmtree(work_dir)
            
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"{filename.rsplit('.', 1)[0]}_images.zip"
            )
            
        except Exception as e:
            # 清理临时文件
            shutil.rmtree(work_dir)
            flash(f'处理PDF时出错: {str(e)}')
            return redirect(url_for('index'))
    
    flash('只允许上传PDF文件')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)