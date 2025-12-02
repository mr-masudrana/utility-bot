from flask import Flask, request, redirect
import os
import requests
import random
import string
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SHEET_NAME = os.environ.get('SHEET_NAME')
GOOGLE_CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS')

# --- Google Sheets কানেকশন ফাংশন ---
def save_to_sheet(email, password):
    try:
        if not GOOGLE_CREDENTIALS or not SHEET_NAME:
            return False, "⚠️ Credentials or Sheet Name missing in Vercel."

        # JSON ক্রেডেনশিয়াল লোড করা
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # শিট ওপেন করা এবং ডাটা অ্যাপেন্ড করা
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row([email, password])
        return True, "✅ Saved to Google Sheet!"
    except Exception as e:
        print(f"Sheet Error: {e}")
        return False, f"❌ Error saving: {str(e)}"

# --- অটো রিডাইরেক্ট ---
def get_bot_username():
    try:
        response = requests.get(f"{BASE_URL}/getMe")
        return response.json()["result"]["username"]
    except:
        return "Telegram"

# --- জিমেইল জেনারেটর ---
def generate_credentials():
    vowels = "aeiou"
    consonants = "bcdfghjklmnpqrstvwxyz"
    name = ""
    for i in range(3):
        name += random.choice(consonants)
        name += random.choice(vowels)
    numbers = ''.join(random.choices(string.digits, k=4))
    email = f"{name}{numbers}@gmail.com"
    chars = string.ascii_letters + string.digits
    password = ''.join(random.choices(chars, k=10))
    return email, password

# --- মেসেজ পাঠানো ---
def send_message(chat_id, text, buttons=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
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
        
        # --- BUTTON CLICK HANDLING ---
        if "callback_query" in data:
            call = data["callback_query"]
            chat_id = call["message"]["chat"]["id"]
            msg_id = call["message"]["message_id"]
            action = call["data"]
            
            # আগের মেসেজ থেকে ইমেইল ও পাসওয়ার্ড বের করা (Regex দিয়ে)
            original_text = call["message"].get("text", "")
            email_match = re.search(r"Email:\s*([^\n]+)", original_text)
            pass_match = re.search(r"Password:\s*([^\n]+)", original_text)
            
            email = email_match.group(1).strip() if email_match else None
            password = pass_match.group(1).strip() if pass_match else None

            # 1. GENERATE NEW
            if action == "gen_gmail":
                new_email, new_password = generate_credentials()
                response = (
                    "🤖 <b>Gmail Generator</b>\n\n"
                    f"📧 <b>Email:</b> <code>{new_email}</code>\n"
                    f"🔑 <b>Password:</b> <code>{new_password}</code>\n\n"
                    "সেভ করতে চাইলে <b>Done</b> চাপুন।"
                )
                buttons = {
                    "inline_keyboard": [
                        [{"text": "✅ Done (Save)", "callback_data": "save_sheet"}, {"text": "❌ Cancel", "callback_data": "cancel"}],
                        [{"text": "🔄 Generate Another", "callback_data": "gen_gmail"}]
                    ]
                }
                # এডিট না করে নতুন মেসেজ পাঠানো (যাতে আগেরগুলো হিস্টোরি থাকে)
                send_message(chat_id, response, buttons)

            # 2. SAVE TO SHEET (DONE)
            elif action == "save_sheet":
                if email and password:
                    # লোডিং মেসেজ (Toast)
                    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": call["id"], "text": "Saving...", "show_alert": False})
                    
                    # শিটে সেভ করা
                    success, msg = save_to_sheet(email, password)
                    
                    if success:
                        new_text = original_text + "\n\n✅ <b>Saved to Sheet!</b>"
                        # বাটন সরিয়ে দেওয়া (যাতে দুইবার সেভ না হয়)
                        requests.post(f"{BASE_URL}/editMessageText", json={
                            "chat_id": chat_id, "message_id": msg_id, "text": new_text, "parse_mode": "HTML"
                        })
                    else:
                         requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": call["id"], "text": msg, "show_alert": True})
                else:
                    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": call["id"], "text": "❌ ডাটা পাওয়া যায়নি!", "show_alert": True})

            # 3. CANCEL
            elif action == "cancel":
                # মেসেজ ডিলিট করে দেওয়া বা ক্যানসেল লেখা
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id})
                requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": call["id"], "text": "Cancelled"})

            else:
                requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": call["id"]})

        # --- TEXT MESSAGE ---
        elif "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                email, password = generate_credentials()
                
                response = (
                    "🤖 <b>Gmail Generator</b>\n\n"
                    f"📧 <b>Email:</b> <code>{email}</code>\n"
                    f"🔑 <b>Password:</b> <code>{password}</code>\n\n"
                    "সেভ করতে চাইলে <b>Done</b> চাপুন।"
                )
                
                buttons = {
                    "inline_keyboard": [
                        [{"text": "✅ Done (Save)", "callback_data": "save_sheet"}, {"text": "❌ Cancel", "callback_data": "cancel"}],
                        [{"text": "🔄 Generate Another", "callback_data": "gen_gmail"}]
                    ]
                }
                send_message(chat_id, response, buttons)

        return "ok", 200

    except Exception as e:
        print(f"Error: {e}")
        return "error", 200
            
