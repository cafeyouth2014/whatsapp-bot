import os
import re
import requests
from flask import Flask, request
from bs4 import BeautifulSoup

app = Flask(__name__)

# ---------------- CONFIG ----------------
TOKEN = "p700o28eapdls2it"
INSTANCE_ID = "instance175339"

# ---------------- LOAD MENU ----------------
with open("menu.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

MENU = {}

items = soup.find_all("div", class_="menu-row")

for item in items:
    spans = item.find_all("span")
    
    if len(spans) >= 2:
        name = spans[0].text.strip().lower()
        price_text = spans[1].text.strip().replace("₹", "")

        try:
            MENU[name] = int(price_text)
        except:
            pass

print("MENU LOADED:", MENU)

# ---------------- BILL CALCULATOR ----------------
def calculate_bill(message):
    lines = message.lower().split("\n")
    total = 0
    summary = ""

    for line in lines:
        match = re.match(r"(\d+)\s(.+)", line.strip())

        if match:
            qty = int(match.group(1))
            customer_item = match.group(2).strip()

            found = False

            for menu_item in MENU:
                if customer_item in menu_item:
                    price = MENU[menu_item]
                    subtotal = qty * price

                    total += subtotal
                    summary += f"{qty} x {menu_item} = ₹{subtotal}\n"

                    found = True
                    break

            if not found:
                summary += f"{customer_item} not found\n"

    return summary, total

# ---------------- SEND MESSAGE ----------------
def send_whatsapp_message(number, message):
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    payload = {
        "token": TOKEN,
        "to": number,
        "body": message
    }

    try:
        response = requests.post(url, data=payload)
        print("WhatsApp Response:", response.text)
    except Exception as e:
        print("Send Error:", e)

# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    print("🔥 WEBHOOK HIT")
    data = request.form
    print("DATA:", data)

    return "ok"

# ---------------- HOME ROUTE ----------------
@app.route("/")
def home():
    return "Bot Running 🚀"

# ---------------- RUN SERVER (RENDER SAFE) ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)