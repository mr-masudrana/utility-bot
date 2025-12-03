from flask import Flask, request, redirect
import os
import requests
import json
import qrcode
import io
import base64
import hashlib
import random
import string
from PIL import Image, ImageOps
from gtts import gTTS
from fpdf import FPDF

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- মেমোরি স্টেট (ইউজার এখন কোন টুলে আছে তা মনে রাখার জন্য) ---
# নোট: Vercel এ সার্ভার রিস্টার্ট হলে এটি মুছে যেতে পারে
user_states = {}

# --- কীবোর্ড মেনু (JSON) ---
def get_main_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🛠 Generator Tool"}, {"text": "📂 PDF Tool"}],
            [{"text": "🗣 Voice Tool"}, {"text": "🖼 Image Tool"}],
            [{"text": "📝 Text Tool"}, {"text": "ℹ️ File Info"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    })

def get_gen_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🟦 QR Code"}, {"text": "🔑 Password Gen"}],
            [{"text": "🔗 Link Shortener"}, {"text": "🔙 Back"}]
        ],
        "resize_keyboard": True
    })

def get_pdf_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🖼 Img to PDF"}, {"text": "📄 Text to PDF"}],
            [{"text": "🔙 Back"}]
        ],
        "resize_keyboard": True
    })

def get_voice_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🗣 Text to Voice"}, {"text": "🔙 Back"}]
        ],
        "resize_keyboard": True
    })

def get_image_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "⚫ Grayscale"}, {"text": "📐 Resize (50%)"}],
            [{"text": "🔙 Back"}]
        ],
        "resize_keyboard": True
    })

def get_text_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🔐 Base64 Enc"}, {"text": "🔓 Base64 Dec"}],
            [{"text": "#️⃣ MD5 Hash"}, {"text": "🔠 Uppercase"}],
            [{"text": "🔙 Back"}]
        ],
        "resize_keyboard": True
    })

# --- হেল্পার ফাংশন ---
def send_reply(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    requests.post(f"{BASE_URL}/sendMessage", json=payload)

def send_file(chat_id, file_data, file_type, caption=None, filename="file"):
    if file_type == "photo":
        files = {'photo': (f"{filename}.jpg", file_data, 'image/jpeg')}
        url = f"{BASE_URL}/sendPhoto"
    elif file_type == "document":
        files = {'document': (f"{filename}.pdf", file_data, 'application/pdf')}
        url = f"{BASE_URL}/sendDocument"
    elif file_type == "audio":
        files = {'audio': (f"{filename}.mp3", file_data, 'audio/mpeg')}
        url = f"{BASE_URL}/sendAudio"
    
    data = {'chat_id': chat_id, 'caption': caption}
    requests.post(url, data=data, files=files)

def get_file_content(file_id):
    # টেলিগ্রাম সার্ভার থেকে ফাইল ডাউনলোড করা
    r = requests.get(f"{BASE_URL}/getFile?file_id={file_id}")
    file_path = r.json()["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    return requests.get(download_url).content

# --- মূল লজিক ---
@app.route('/')
def home():
    return "Swiss Army Bot is Running! 🤖"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if "message" not in data: return "ok", 200

        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        
        # ইউজারের বর্তমান স্টেট চেক করা
        state = user_states.get(chat_id, None)

        # --- ১. নেভিগেশন (Navigation) ---
        if text == "/start" or text == "🔙 Back":
            user_states[chat_id] = None # স্টেট রিসেট
            send_reply(chat_id, "👋 <b>Main Menu</b>\nএকটি টুল সিলেক্ট করুন:", get_main_menu())
            return "ok", 200

        # মেইন মেনু সিলেকশন
        elif text == "🛠 Generator Tool":
            send_reply(chat_id, "🛠 <b>Generator Tools</b>", get_gen_menu())
        elif text == "📂 PDF Tool":
            send_reply(chat_id, "📂 <b>PDF Tools</b>", get_pdf_menu())
        elif text == "🗣 Voice Tool":
            send_reply(chat_id, "🗣 <b>Voice Tools</b>", get_voice_menu())
        elif text == "🖼 Image Tool":
            send_reply(chat_id, "🖼 <b>Image Tools</b>", get_image_menu())
        elif text == "📝 Text Tool":
            send_reply(chat_id, "📝 <b>Text Tools</b>", get_text_menu())
        elif text == "ℹ️ File Info":
            user_states[chat_id] = "file_info"
            send_reply(chat_id, "ℹ️ যেকোনো ফাইল, ছবি বা ভিডিও পাঠান। আমি ইনফো দেব।")

        # --- ২. টুল অ্যাক্টিভেশন (Tool Activation) ---
        
        # Generator
        elif text == "🟦 QR Code":
            user_states[chat_id] = "qr"
            send_reply(chat_id, "👉 QR কোডের জন্য টেক্সট পাঠান:")
        elif text == "🔗 Link Shortener":
            user_states[chat_id] = "shorten"
            send_reply(chat_id, "👉 বড় লিংকটি পাঠান:")
        elif text == "🔑 Password Gen":
            # পাসওয়ার্ড জেনারেটরের ইনপুট লাগে না, তাই সরাসরি দিয়ে দেব
            chars = string.ascii_letters + string.digits + "!@#"
            pwd = ''.join(random.choices(chars, k=12))
            send_reply(chat_id, f"🔑 <b>Generated Password:</b>\n<code>{pwd}</code>")

        # Voice
        elif text == "🗣 Text to Voice":
            user_states[chat_id] = "tts"
            send_reply(chat_id, "👉 যে লেখাটি ভয়েস বানাতে চান তা ইংরেজিতে পাঠান:")

        # Text
        elif text == "🔐 Base64 Enc":
            user_states[chat_id] = "b64_enc"
            send_reply(chat_id, "👉 এনকোড করার জন্য টেক্সট পাঠান:")
        elif text == "🔓 Base64 Dec":
            user_states[chat_id] = "b64_dec"
            send_reply(chat_id, "👉 ডিকোড করার জন্য কোড পাঠান:")
        elif text == "#️⃣ MD5 Hash":
            user_states[chat_id] = "hash"
            send_reply(chat_id, "👉 টেক্সট পাঠান:")
        elif text == "🔠 Uppercase":
            user_states[chat_id] = "upper"
            send_reply(chat_id, "👉 ছোট হাতের লেখা পাঠান:")

        # PDF & Image (State Set)
        elif text == "🖼 Img to PDF":
            user_states[chat_id] = "img2pdf"
            send_reply(chat_id, "👉 একটি ছবি পাঠান (JPG/PNG):")
        elif text == "📄 Text to PDF":
            user_states[chat_id] = "text2pdf"
            send_reply(chat_id, "👉 পিডিএফ বানানোর জন্য টেক্সট পাঠান:")
        elif text == "⚫ Grayscale":
            user_states[chat_id] = "grayscale"
            send_reply(chat_id, "👉 সাদা-কালো করার জন্য ছবি পাঠান:")
        elif text == "📐 Resize (50%)":
            user_states[chat_id] = "resize"
            send_reply(chat_id, "👉 ছোট করার জন্য ছবি পাঠান:")

        # --- ৩. ইনপুট প্রসেসিং (Input Processing) ---
        else:
            # যদি টেক্সট মেসেজ হয়
            if text and state:
                if state == "qr":
                    img = qrcode.make(text)
                    bio = io.BytesIO()
                    img.save(bio, 'PNG')
                    bio.seek(0)
                    send_file(chat_id, bio, "photo", caption="✅ QR Code Generated")
                
                elif state == "shorten":
                    try:
                        res = requests.get(f"http://tinyurl.com/api-create.php?url={text}")
                        send_reply(chat_id, f"🔗 <b>Short Link:</b>\n{res.text}")
                    except: send_reply(chat_id, "⚠️ লিংকটি সঠিক নয়।")

                elif state == "tts":
                    try:
                        tts = gTTS(text, lang='en')
                        bio = io.BytesIO()
                        tts.write_to_fp(bio)
                        bio.seek(0)
                        send_file(chat_id, bio, "audio", caption="🗣 Generated Voice")
                    except: send_reply(chat_id, "⚠️ টেক্সট টু স্পিচ এরর।")

                elif state == "b64_enc":
                    res = base64.b64encode(text.encode()).decode()
                    send_reply(chat_id, f"🔐 Result: <code>{res}</code>")
                
                elif state == "b64_dec":
                    try:
                        res = base64.b64decode(text).decode()
                        send_reply(chat_id, f"🔓 Result: <code>{res}</code>")
                    except: send_reply(chat_id, "⚠️ ভুল ফরম্যাট।")

                elif state == "hash":
                    res = hashlib.md5(text.encode()).hexdigest()
                    send_reply(chat_id, f"#️⃣ Hash: <code>{res}</code>")

                elif state == "upper":
                    send_reply(chat_id, f"🔠: {text.upper()}")

                elif state == "text2pdf":
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    # ইউনিকোড সাপোর্ট ফ্রী ভার্সনে সীমিত, তাই ইংরেজি টেক্সট ভালো কাজ করবে
                    pdf.multi_cell(0, 10, text.encode('latin-1', 'replace').decode('latin-1'))
                    bio = io.BytesIO()
                    # FPDF output as string, encode to bytes
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    bio.write(pdf_output)
                    bio.seek(0)
                    send_file(chat_id, bio, "document", caption="✅ Text to PDF", filename="text_doc")

            # যদি ছবি বা ফাইল হয়
            elif (msg.get("photo") or msg.get("document")) and state:
                # ফাইল ইনফো মোড
                if state == "file_info":
                    f_size = 0
                    f_type = "Unknown"
                    if "photo" in msg:
                        f = msg["photo"][-1]
                        f_size = f["file_size"]
                        f_type = f"Photo ({f['width']}x{f['height']})"
                    elif "document" in msg:
                        f_size = msg["document"]["file_size"]
                        f_type = f"Document ({msg['document']['mime_type']})"
                    elif "video" in msg:
                        f_size = msg["video"]["file_size"]
                        f_type = "Video"
                    
                    mb_size = round(f_size / (1024*1024), 2)
                    send_reply(chat_id, f"📂 <b>File Info:</b>\nType: {f_type}\nSize: {mb_size} MB")

                # ইমেজ প্রসেসিং মোড
                elif "photo" in msg and state in ["img2pdf", "grayscale", "resize"]:
                    file_id = msg["photo"][-1]["file_id"]
                    img_bytes = get_file_content(file_id)
                    img = Image.open(io.BytesIO(img_bytes))
                    bio = io.BytesIO()

                    if state == "img2pdf":
                        img.convert('RGB').save(bio, 'PDF')
                        bio.seek(0)
                        send_file(chat_id, bio, "document", caption="✅ Image to PDF", filename="image_doc")
                    
                    elif state == "grayscale":
                        img = ImageOps.grayscale(img)
                        img.save(bio, 'JPEG')
                        bio.seek(0)
                        send_file(chat_id, bio, "photo", caption="⚫ Grayscale Image")

                    elif state == "resize":
                        w, h = img.size
                        img = img.resize((int(w/2), int(h/2)))
                        img.save(bio, 'JPEG')
                        bio.seek(0)
                        send_file(chat_id, bio, "photo", caption="📐 Resized (50%)")

            # যদি স্টেট সিলেক্ট করা না থাকে
            elif not state and text not in ["/start", "🔙 Back"]:
                send_reply(chat_id, "⚠️ দয়া করে প্রথমে মেনু থেকে একটি টুল সিলেক্ট করুন।", get_main_menu())

        return "ok", 200

    except Exception as e:
        print(f"Error: {e}")
        return "error", 200
