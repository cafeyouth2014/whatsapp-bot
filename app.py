import requests
from flask import Flask
from bs4 import BeautifulSoup

app = Flask(__name__)

TOKEN = "p700o28eapdls2it"
INSTANCE_ID = "instance175339"

# MENU HTML READ
with open("menu.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

MENU = {}

# SAARE MENU ITEMS FIND KARO
items = soup.find_all("div", class_="menu-row")

for item in items:

    spans = item.find_all("span")

    # ITEM NAME
    name = spans[0].text.strip().lower()

    # PRICE
    price = spans[1].text.strip().replace("₹", "")

    try:
        MENU[name] = int(price)
    except:
        pass

print(MENU)

import re

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

def send_whatsapp_message(number, message):

    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    payload = {
        "token": TOKEN,
        "to": number,
        "body": message
    }

    response = requests.post(url, data=payload)

    print(response.text)

from flask import request

@app.route("/webhook", methods=["POST"])
def webhook():
    
    print("WEBHOOK HIT")

    data = request.form

    message = data.get("body", "").lower()

    sender = data.get("from", "")

    print(message)

    print(sender)

    summary, total = calculate_bill(message)

    reply = f"""
Thank you for your order ❤️

{summary}

Total = ₹{total}
"""

    send_whatsapp_message(sender, reply)

    return "ok"

@app.route("/")
def home():
    return "Bot Running"

if __name__ == "__main__":
    app.run(debug=True)