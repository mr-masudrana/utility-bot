from flask import Flask, request, redirect
import os
import requests
import json

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- ১. মেনু বাটন ডিজাইন (JSON Format) ---

# মেইন মেনু (Main Menu)
main_menu = {
    "keyboard": [
        [{"text": "🛠 Generator Tool"}, {"text": "Cc PDF Tool"}],
        [{"text": "🗣 Voice Tool"}, {"text": "🖼 Image Tool"}],
        [{"text": "📝 Text Tool"}, {"text": "📂 File Info"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

# জেনারেটর সাব-মেনু
gen_menu = {
    "keyboard": [
        [{"text": "🟦 QR Code"}, {"text": "asd Password Gen"}],
        [{"text": "🔗 Link Shortener"}, {"text": "🔙 Back"}]
    ],
    "resize_keyboard": True
}

# পিডিএফ সাব-মেনু
pdf_menu = {
    "keyboard": [
        [{"text": "🖼 Img to PDF"}, {"text": "📄 Text to PDF"}],
        [{"text": "🖇 Merge PDF"}, {"text": "🔙 Back"}]
    ],
    "resize_keyboard": True
}

# ভয়েস সাব-মেনু
voice_menu = {
    "keyboard": [
        [{"text": "🗣 Text to Voice"}, {"text": "🎤 Voice to Text"}],
        [{"text": "🔙 Back"}]
    ],
    "resize_keyboard": True
}

# ইমেজ সাব-মেনু
image_menu = {
    "keyboard": [
        [{"text": "✂️ Remove BG"}, {"text": "📐 Resize"}],
        [{"text": "🔙 Back"}]
    ],
    "resize_keyboard": True
}

# টেক্সট সাব-মেনু
text_menu = {
    "keyboard": [
        [{"text": "🔐 Base64 Encode"}, {"text": "#️⃣ Hash Gen"}],
        [{"text": "🔠 Case Converter"}, {"text": "🔙 Back"}]
    ],
    "resize_keyboard": True
}

# --- মেসেজ পাঠানোর ফাংশন ---
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    # যদি বাটন থাকে তবে যোগ করবে
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        requests.post(f"{BASE_URL}/sendMessage", json=payload)
    except Exception as e:
        print(f"Error: {e}")

@app.route('/')
def home():
    return "Menu Bot is Running! 🤖"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        
        if "message" in data and "text" in data["message"]:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            text = msg["text"]
            
            # --- ১. মেইন মেনু লজিক ---
            if text == "/start" or text == "🔙 Back":
                send_message(chat_id, "👋 <b>Main Menu</b>\nনিচ থেকে একটি টুল সিলেক্ট করুন:", main_menu)

            # --- ২. সাব-মেনু ওপেন করার লজিক ---
            
            elif text == "🛠 Generator Tool":
                send_message(chat_id, "🛠 <b>Generator Tools</b>\nকি জেনারেট করতে চান?", gen_menu)
                
            elif text == "Cc PDF Tool":
                send_message(chat_id, "Cc <b>PDF Tools</b>\nএকটি অপশন বেছে নিন:", pdf_menu)
                
            elif text == "🗣 Voice Tool":
                send_message(chat_id, "🗣 <b>Voice Tools</b>\nঅপশন সিলেক্ট করুন:", voice_menu)
                
            elif text == "🖼 Image Tool":
                send_message(chat_id, "🖼 <b>Image Tools</b>\nকি করতে চান?", image_menu)
                
            elif text == "📝 Text Tool":
                send_message(chat_id, "📝 <b>Text Tools</b>\nটেক্সট টুলস ওপেন হয়েছে:", text_menu)
                
            elif text == "📂 File Info":
                # ফাইল ইনফো সাব-মেনু নেই, এটি সরাসরি কাজ করবে
                send_message(chat_id, "📂 যেকোনো ফাইল বা ছবি পাঠান, আমি ইনফো দেব।\n(ফিরে যেতে <b>Back</b> চাপুন)", main_menu)

            # --- ৩. টুলের কাজ (উদাহরণ: QR Code) ---
            elif text == "🟦 QR Code":
                send_message(chat_id, "অনুগ্রহ করে টেক্সট বা লিংক পাঠান, আমি QR Code বানিয়ে দেব।")
                # এখানে QR কোড তৈরির লজিক বসাতে হবে (আগের কোড অনুযায়ী)
            
            elif text == "asd Password Gen":
                send_message(chat_id, "আপনার পাসওয়ার্ড: <code>XyZ123!@</code>")

            # --- ৪. ডিফল্ট মেসেজ ---
            else:
                # যদি ইউজার টুল সিলেক্ট করা ছাড়াই কিছু লেখে
                send_message(chat_id, "⚠️ দয়া করে নিচের বাটনগুলো ব্যবহার করুন।", main_menu)

        return "ok", 200

    except Exception as e:
        print(f"Error: {e}")
        return "error", 200
