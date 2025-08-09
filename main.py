from flask import Flask, render_template, request, send_file, redirect, flash
from werkzeug.utils import secure_filename
import os
from pypdf import PdfReader, PdfWriter
import pdfplumber
import uuid
import html
# import flitz

app = Flask(__name__)
app.secret_key = "123"
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def unique_filename(filename):
    # สร้างชื่อไฟล์ไม่ซ้ำกัน
    name, ext = os.path.splitext(filename)
    return f"{name}_{uuid.uuid4().hex}{ext}"

@app.route('/')
def index():
    return render_template("index.html")

# 🔓 ลบรหัสผ่าน PDF
@app.route('/decrypt', methods=['POST'])
def decrypt_pdf():
    file = request.files['pdf_file']
    password = request.form.get('password', '')
    filename = unique_filename(secure_filename(file.filename))
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)

    try:
        reader = PdfReader(input_path)
        if reader.is_encrypted:
            reader.decrypt(password)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_path = os.path.join(UPLOAD_FOLDER, f'decrypted_{filename}')
        with open(output_path, 'wb') as f:
            writer.write(f)

        os.remove(input_path)  # ลบไฟล์ต้นฉบับ
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        flash(f"Error: {str(e)}")
        if os.path.exists(input_path):
            os.remove(input_path)
        return redirect('/')
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

# ➕ รวม PDF
@app.route('/merge', methods=['POST'])
def merge_pdf():
    files = request.files.getlist('pdfs')
    writer = PdfWriter()
    temp_paths = []

    for file in files:
        filename = unique_filename(secure_filename(file.filename))
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        temp_paths.append(path)
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)

    output_path = os.path.join(UPLOAD_FOLDER, f'merged_{uuid.uuid4().hex}.pdf')
    with open(output_path, 'wb') as f:
        writer.write(f)

    # ลบไฟล์ต้นฉบับ
    for path in temp_paths:
        if os.path.exists(path):
            os.remove(path)
    return send_file(output_path, as_attachment=True)
    # ลบไฟล์ผลลัพธ์หลังส่ง
    # (ใช้ after_this_request ถ้าต้องการลบหลังส่งจริง ๆ)

# ✂️ แยกหน้า PDF
@app.route('/split', methods=['POST'])
def split_pdf():
    file = request.files['pdf_file']
    pages_str = request.form.get('page_num', '')  # รับ string
    filename = unique_filename(secure_filename(file.filename))
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)

    # แปลง string เป็น list ของเลขหน้า (0-indexed)
    # ตัดช่องว่าง, comma, pipe
    import re
    pages = re.split(r'[ ,|]+', pages_str.strip())
    pages = [int(p)-1 for p in pages if p.isdigit()]  # หน้าเริ่มที่ 1, แต่ในโค้ดเริ่มที่ 0

    reader = PdfReader(input_path)
    writer = PdfWriter()

    # เพิ่มหน้าใน list ถ้าเกินจำนวนหน้าของ PDF จะข้าม
    for p in pages:
        if 0 <= p < len(reader.pages):
            writer.add_page(reader.pages[p])

    output_path = os.path.join(UPLOAD_FOLDER, f'split_{filename}')
    with open(output_path, 'wb') as f:
        writer.write(f)

    os.remove(input_path)
    return send_file(output_path, as_attachment=True)

# 📄 ดึงข้อความจาก PDF
@app.route('/extract', methods=['POST'])
def extract_text():
    file = request.files['pdf_file']
    filename = unique_filename(secure_filename(file.filename))
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)

    text_output = extract_text_preserve_layout(input_path)

    os.remove(input_path)
    safe_text = html.escape(text_output)  # ป้องกัน XSS
    return f"<h2>Extracted Text (with layout):</h2><pre style='white-space: pre-wrap;'>{safe_text}</pre><br><a href='/'>← กลับ</a>"

if __name__ == '__main__':
    app.run(debug=True)