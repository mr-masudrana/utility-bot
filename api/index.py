from flask import Flask, request, redirect
import os
import requests
import random
import string

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- অটো রিডাইরেক্টের জন্য ---
def get_bot_username():
    try:
        response = requests.get(f"{BASE_URL}/getMe")
        return response.json()["result"]["username"]
    except:
        return "Telegram"

# --- জিমেইল এবং পাসওয়ার্ড জেনারেটর ---
def generate_credentials():
    # ১. ভাওয়েল এবং কনসোন্যান্ট দিয়ে মানুষের মতো নাম তৈরি করা (উচ্চারণযোগ্য)
    vowels = "aeiou"
    consonants = "bcdfghjklmnpqrstvwxyz"
    
    # ৬-৭ অক্ষরের নাম তৈরি
    name = ""
    for i in range(3):
        name += random.choice(consonants)
        name += random.choice(vowels)
    
    # শেষে ৩-৪ ডিজিটের সংখ্যা যোগ করা (যাতে ইউনিক হয়)
    numbers = ''.join(random.choices(string.digits, k=4))
    
    email = f"{name}{numbers}@gmail.com"
    
    # ২. শক্তিশালী পাসওয়ার্ড তৈরি (Upper + Lower + Digit)
    chars = string.ascii_letters + string.digits
    password = ''.join(random.choices(chars, k=10))
    
    return email, password

# --- মেসেজ পাঠানো ---
def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    if buttons: payload["reply_markup"] = buttons
    try: requests.post(f"{BASE_URL}/sendMessage", json=payload)
    except: pass

@app.route('/')
def home():
    return redirect(f"https://t.me/{get_bot_username()}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        
        # --- BUTTON CLICK ---
        if "callback_query" in data:
            call = data["callback_query"]
            chat_id = call["message"]["chat"]["id"]
            
            if call["data"] == "gen_gmail":
                email, password = generate_credentials()
                
                response = (
                    "✅ <b>Gmail Suggestion Generated!</b>\n\n"
                    f"📧 <b>Email:</b> <code>{email}</code>\n"
                    f"🔑 <b>Password:</b> <code>{password}</code>\n\n"
                    "⚠️ <i>এটি শুধু একটি সাজেশন। আপনি এই তথ্য দিয়ে সাইন-আপ করার চেষ্টা করুন।</i>"
                )
                
                buttons = {
                    "inline_keyboard": [
                        [{"text": "📝 Create Account Now", "url": "https://accounts.google.com/signup"}],
                        [{"text": "🔄 Generate Another", "callback_data": "gen_gmail"}]
                    ]
                }
                
                # আগের মেসেজ এডিট না করে নতুন মেসেজ পাঠানো (যাতে আগেরগুলো সেভ থাকে)
                send_message(chat_id, response, buttons)
            
            # লোডিং আইকন বন্ধ করা
            requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": call["id"]})

        # --- TEXT MESSAGE ---
        elif "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                email, password = generate_credentials()
                
                response = (
                    "🤖 <b>Gmail ID Generator Bot</b>\n\n"
                    "আমি ইউনিক জিমেইল আইডি এবং পাসওয়ার্ড সাজেস্ট করি যা সাধারণত খালি (Available) থাকে।\n\n"
                    f"📧 <b>Email:</b> <code>{email}</code>\n"
                    f"🔑 <b>Password:</b> <code>{password}</code>"
                )
                
                buttons = {
                    "inline_keyboard": [
                        [{"text": "📝 Create Account Now", "url": "https://accounts.google.com/signup"}],
                        [{"text": "🔄 Generate Another", "callback_data": "gen_gmail"}]
                    ]
                }
                send_message(chat_id, response, buttons)

        return "ok", 200

    except Exception as e:
        print(f"Error: {e}")
        return "error", 200
        
