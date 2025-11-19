Instagram Supplier Bot (Order Only • No Stock System • Manual Delivery)

---------------------------------------------------------------

Features:

- Telegram bot (aiogram)

- No stock / no accounts system

- Order creation only

- After payment → "Team will contact you" message

- Data saved in JSON (users, products, orders)

- Broadcast system included

---------------------------------------------------------------

import json import os import asyncio from aiogram import Bot, Dispatcher, types from aiogram.types import ReplyKeyboardMarkup, KeyboardButton from aiogram.utils import exceptions from datetime import datetime

BOT_TOKEN = "7848720803:AAG3rU2bRB3BBB6iI0-BNgxqneTO0DU0ewA" ADMIN_ID = 6675623588

------------------------ FILE PATHS ------------------------

DATA_DIR = "data" USERS_FILE = f"{DATA_DIR}/users.json" PRODUCTS_FILE = f"{DATA_DIR}/products.json" ORDERS_FILE = f"{DATA_DIR}/orders.json"

os.makedirs(DATA_DIR, exist_ok=True)

------------------------ JSON LOAD/SAVE ------------------------

def load_json(path, default): if not os.path.exists(path): save_json(path, default) with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_json(path, data): with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

users = load_json(USERS_FILE, []) products = load_json(PRODUCTS_FILE, []) orders = load_json(ORDERS_FILE, [])

------------------------ BOT SETUP ------------------------

bot = Bot(token=BOT_TOKEN) dp = Dispatcher(bot)

main_kb = ReplyKeyboardMarkup(resize_keyboard=True) main_kb.add(KeyboardButton("Browse Products")) main_kb.add(KeyboardButton("My Orders")) main_kb.add(KeyboardButton("Support"))

------------------------ SAVE ALL ------------------------

def save_all(): save_json(USERS_FILE, users) save_json(PRODUCTS_FILE, products) save_json(ORDERS_FILE, orders)

------------------------ START ------------------------

@dp.message_handler(commands=["start"]) async def start_cmd(msg: types.Message): uid = msg.from_user.id if uid not in users: users.append(uid) save_all() await msg.reply("Welcome! Choose an option.", reply_markup=main_kb)

------------------------ BROWSE PRODUCTS ------------------------

@dp.message_handler(lambda m: m.text == "Browse Products") async def browse(msg: types.Message): if not products: return await msg.reply("No products available.")

text = "Available Products:

" for p in products: text += f"ID: {p['id']} | {p['name']} | Price: ₹{p['price']} " text += " To order: /order <product_id> <qty>"

await msg.reply(text)

------------------------ ORDER CREATION ------------------------

@dp.message_handler(commands=["order"]) async def order_cmd(msg: types.Message): try: _, pid, qty = msg.text.split() pid = int(pid) qty = int(qty) except: return await msg.reply("Format: /order <product_id> <qty>")

product = next((p for p in products if p["id"] == pid), None)
if not product:
    return await msg.reply("Invalid product ID.")

order_id = len(orders) + 1
amount = product["price"] * qty

new_order = {
    "id": order_id,
    "user": msg.from_user.id,
    "product_id": pid,
    "qty": qty,
    "amount": amount,
    "status": "pending_payment",
    "created": str(datetime.now())
}

orders.append(new_order)
save_all()

pay_text = (
    f"Order Created!

Order ID: {order_id} Amount: ₹{amount}

" "Send: PAYMENT <order_id> after you pay and attach screenshot." ) await msg.reply(pay_text)

# Notify admin
await bot.send_message(ADMIN_ID, f"New order {order_id} from {msg.from_user.id}")

------------------------ PAYMENT CONFIRMATION ------------------------

@dp.message_handler(lambda m: m.text.startswith("PAYMENT")) async def handle_payment(msg: types.Message): try: _, oid = msg.text.split() oid = int(oid) except: return await msg.reply("Format: PAYMENT <order_id>")

order = next((o for o in orders if o["id"] == oid), None)
if not order:
    return await msg.reply("Order not found.")

order["status"] = "paid"
order["confirmed_at"] = str(datetime.now())
save_all()

# User message
await msg.reply(
    "✅ Payment Received!

" "Our team will contact you shortly for delivery." )

# Admin message
await bot.send_message(ADMIN_ID, f"Order {oid} marked PAID. Contact user {order['user']}")

------------------------ MY ORDERS ------------------------

@dp.message_handler(lambda m: m.text == "My Orders") async def my_orders(msg: types.Message): my = [o for o in orders if o["user"] == msg.from_user.id] if not my: return await msg.reply("No orders yet.")

text = "Your Orders:

" for o in my: text += f"ID {o['id']} | Qty {o['qty']} | ₹{o['amount']} | {o['status']} "

await msg.reply(text)

------------------------ SUPPORT ------------------------

@dp.message_handler(lambda m: m.text == "Support") async def support_msg(msg: types.Message): await msg.reply("Send your issue. Admin will contact you.")

------------------------ BROADCAST ------------------------

@dp.message_handler(commands=["broadcast"]) async def admin_broadcast(msg: types.Message): if msg.from_user.id != ADMIN_ID: return

message = msg.text.replace("/broadcast", "").strip()
if not message:
    return await msg.reply("Usage: /broadcast your message text")

await msg.reply(f"Broadcasting to {len(users)} users...")

sent = 0
for uid in users:
    try:
        await bot.send_message(uid, message)
        await asyncio.sleep(0.05)
        sent += 1
    except:
        pass

await msg.reply(f"Broadcast sent to {sent}/{len(users)} users.")

------------------------ RUN BOT ------------------------

async def main(): print("Bot running...") await dp.start_polling()

if name == "main": asyncio.run(main())