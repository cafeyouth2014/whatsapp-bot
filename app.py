import os
import re
import json
import requests
from flask import Flask, request
from bs4 import BeautifulSoup

app = Flask(__name__)

# ---------------- CONFIG ----------------
TOKEN = "p700o28eapdls2it"
INSTANCE_ID = "instance175339"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY_HERE")

# ---------------- LOAD MENU ----------------
with open("menu.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
MENU = {}

sections = soup.find_all("div", class_="section")
for section in sections:
    rows = section.find_all("div", class_="menu-row")
    for row in rows:
        spans = row.find_all("span")
        if len(spans) == 3:
            name = spans[0].text.strip().lower()
            veg_price = spans[1].text.strip().replace("₹", "").replace(",", "")
            nonveg_price = spans[2].text.strip().replace("₹", "").replace(",", "")
            try:
                MENU[name] = {"veg": int(veg_price), "nonveg": int(nonveg_price)}
            except:
                pass
        elif len(spans) == 2:
            name = spans[0].text.strip().lower()
            price_text = spans[1].text.strip().replace("₹", "").replace(",", "")
            try:
                MENU[name] = {"only": int(price_text)}
            except:
                pass

print("✅ MENU LOADED:", list(MENU.keys()))

# ---------------- MENU STRING FOR AI ----------------
def get_menu_string():
    lines = []
    for item, prices in MENU.items():
        if "only" in prices:
            lines.append(f"{item}: ₹{prices['only']}")
        else:
            lines.append(f"{item}: veg ₹{prices.get('veg','?')}, non-veg ₹{prices.get('nonveg','?')}")
    return "\n".join(lines)

# ---------------- GEMINI AI ORDER PARSER ----------------
def parse_order_with_ai(customer_message):
    menu_str = get_menu_string()

    prompt = f"""You are an order parser for a cafe called "Cafe Youth".

Here is the cafe menu with prices:
{menu_str}

A customer sent this message:
"{customer_message}"

Your job:
1. Understand what items the customer wants to order, even if they write casually in Hindi, English, or Hinglish.
2. Match each item to the closest menu item.
3. If quantity is not mentioned, assume 1.
4. If veg/non-veg not mentioned for items that have both options, assume veg.
5. Return ONLY a JSON array, no explanation, no markdown, just raw JSON like this:

[
  {{"item": "exact menu item name", "qty": 1, "type": "veg"}},
  {{"item": "exact menu item name", "qty": 2, "type": "nonveg"}},
  {{"item": "exact menu item name", "qty": 1, "type": "only"}}
]

Use "only" as type for items that don't have veg/nonveg distinction.
If the message is NOT an order (like greetings, questions, random text), return an empty array: []
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, json=payload)
        result = response.json()
        ai_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        ai_text = re.sub(r"```json|```", "", ai_text).strip()
        parsed = json.loads(ai_text)
        return parsed
    except Exception as e:
        print("❌ Gemini Error:", e)
        return None

# ---------------- BILL CALCULATOR ----------------
def calculate_bill(parsed_order):
    total = 0
    summary_lines = []
    errors = []

    for item_obj in parsed_order:
        item_name = item_obj.get("item", "").lower().strip()
        qty = int(item_obj.get("qty", 1))
        item_type = item_obj.get("type", "veg")

        if item_name in MENU:
            prices = MENU[item_name]
            if item_type == "only" and "only" in prices:
                price = prices["only"]
            elif item_type == "nonveg" and "nonveg" in prices:
                price = prices["nonveg"]
            elif "veg" in prices:
                price = prices["veg"]
            elif "only" in prices:
                price = prices["only"]
            else:
                price = list(prices.values())[0]

            subtotal = qty * price
            total += subtotal
            summary_lines.append(f"  {qty} x {item_name.title()} = ₹{subtotal}")
        else:
            errors.append(f"  ❌ '{item_name}' not found")

    return summary_lines, errors, total

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
        print("📤 WhatsApp Response:", response.text)
    except Exception as e:
        print("❌ Send Error:", e)

# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📥 Incoming:", json.dumps(data, indent=2))

        msg_data = data.get("data", {})
        msg_type = msg_data.get("type", "")
        from_number = msg_data.get("from", "")
        body = msg_data.get("body", "").strip()

        if msg_type != "chat" or not body:
            return "ok", 200

        if msg_data.get("fromMe", False):
            return "ok", 200

        print(f"📨 Message from {from_number}: {body}")

        parsed_order = parse_order_with_ai(body)

        if parsed_order is None:
            reply = "Sorry, kuch technical issue aa gaya! Thodi der baad try karo. 🙏"

        elif len(parsed_order) == 0:
            reply = (
                "👋 *Cafe Youth mein aapka swagat hai!*\n\n"
                "Order karne ke liye bas likh do kya chahiye, jaise:\n"
                "_'ek hakka noodles veg aur ek cold coffee'_\n\n"
                "Hum turant confirm kar denge! ☕😊"
            )

        else:
            summary_lines, errors, total = calculate_bill(parsed_order)

            if total > 0:
                items_text = "\n".join(summary_lines)
                reply = (
                    f"✅ *Thank you for ordering from Cafe Youth!*\n\n"
                    f"*Your Order:*\n{items_text}\n\n"
                    f"*Total Amount: ₹{total}*\n\n"
                    f"Thank you! 🙏\n"
                    f"_Fun, Frndz & Gupshup ☕_"
                )
                if errors:
                    reply += "\n\n⚠️ *Yeh items menu mein nahi mile:*\n" + "\n".join(errors)
            else:
                reply = (
                    "❌ Sorry, yeh items humare menu mein nahi hain.\n"
                    "Kripya menu dekh ke dobara order karein! 😊"
                )

        send_whatsapp_message(from_number, reply)

    except Exception as e:
        print("❌ Webhook Error:", e)

    return "ok", 200

# ---------------- HOME ----------------
@app.route("/")
def home():
    return "Cafe Youth Bot Running 🚀☕"

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)