from flask import Flask, request, redirect
import os
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- ইউজারনেম বের করা (Redirect এর জন্য) ---
def get_bot_username():
    try:
        response = requests.get(f"{BASE_URL}/getMe")
        return response.json()["result"]["username"]
    except:
        return "Telegram"

# --- মেটা ডাটা স্ক্র্যাপার ফাংশন ---
def get_social_info(url):
    # ফেসবুক/ইনস্টাগ্রাম বট হিসেবে পরিচয় দিলে অনেক সময় পেজ লোড করতে দেয়
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None, "Server blocked the request"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ১. নাম বের করা (og:title)
        title_tag = soup.find("meta", property="og:title")
        name = title_tag["content"] if title_tag else "Unknown Name"
        
        # ২. ছবি বের করা (og:image)
        image_tag = soup.find("meta", property="og:image")
        image_url = image_tag["content"] if image_tag else None
        
        # ৩. ইউজার আইডি খোঁজার চেষ্টা (খুব কঠিন, তাই রেগুলার এক্সপ্রেশন ব্যবহার করা হলো)
        user_id = "Hidden/Not Found"
        
        # ফেসবুকের জন্য আইডি খোঁজা
        if "facebook.com" in url:
            # সোর্স কোডের ভেতর userID বা entity_id খোঁজা
            id_match = re.search(r'"userID":"(\d+)"', response.text)
            if not id_match:
                id_match = re.search(r'"entity_id":"(\d+)"', response.text)
            
            if id_match:
                user_id = id_match.group(1)
        
        # ইনস্টাগ্রামের জন্য আইডি খোঁজা
        elif "instagram.com" in url:
             id_match = re.search(r'"profile_id":"(\d+)"', response.text)
             if id_match:
                 user_id = id_match.group(1)

        return {
            "name": name,
            "image": image_url,
            "id": user_id,
            "source": "Facebook" if "facebook" in url else "Instagram"
        }, None

    except Exception as e:
        return None, str(e)

# --- মেসেজ পাঠানো ---
def send_reply(chat_id, text, photo=None):
    if photo:
        url = f"{BASE_URL}/sendPhoto"
        payload = {"chat_id": chat_id, "photo": photo, "caption": text, "parse_mode": "HTML"}
    else:
        url = f"{BASE_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    
    requests.post(url, json=payload)

@app.route('/')
def home():
    return redirect(f"https://t.me/{get_bot_username()}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if "message" not in data: return "ok", 200
        
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            send_reply(chat_id, "👋 <b>Social Profile Finder</b>\n\nআমাকে Facebook বা Instagram প্রোফাইলের লিংক দিন।\nআমি নাম এবং ছবি বের করে দেব।")
        
        elif "facebook.com" in text or "instagram.com" in text:
            send_reply(chat_id, "🔍 <b>Searching...</b> (একটু সময় লাগতে পারে)")
            
            info, error = get_social_info(text)
            
            if info:
                caption = (
                    f"✅ <b>Profile Found!</b>\n\n"
                    f"📛 <b>Name:</b> {info['name']}\n"
                    f"🆔 <b>User ID:</b> <code>{info['id']}</code>\n"
                    f"🌐 <b>Source:</b> {info['source']}"
                )
                # যদি ছবি পাওয়া যায় তবে ছবিসহ, না হলে শুধু টেক্সট
                if info['image']:
                    send_reply(chat_id, caption, photo=info['image'])
                else:
                    send_reply(chat_id, caption)
            else:
                send_reply(chat_id, f"⚠️ তথ্য পাওয়া যায়নি। সম্ভবত প্রোফাইল লক করা বা সার্ভার ব্লক করেছে।\nError: {error}")
        
        else:
            send_reply(chat_id, "⚠️ দয়া করে সঠিক Facebook বা Instagram লিংক দিন।")

        return "ok", 200

    except Exception as e:
        print(f"Error: {e}")
        return "error", 200
        
