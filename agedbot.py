# Instagram Supplier Bot (Order Only - No Stock System - Manual Delivery)

# ---------------------------------------------------------------
# ---------------------------------------------------------------
#
# Features:
#
# - Telegram bot (aiogram)
#
# - No stock / no accounts system
#
# - Order creation only
#
# - After payment → "Team will contact you" message
#
# - Data saved in JSON (users, products, orders)
#
# - Broadcast system included
#
# ---------------------------------------------------------------

import json
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

BOT_TOKEN = "7848720803:AAG3rU2bRB3BBB6iI0-BNgxqneTO0DU0ewA"
ADMIN_ID = 6675623588

# ------------------------ FILE PATHS ------------------------

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
PRODUCTS_FILE = f"{DATA_DIR}/products.json"
ORDERS_FILE = f"{DATA_DIR}/orders.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------ JSON LOAD/SAVE ------------------------

def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

users = load_json(USERS_FILE, [])
products = load_json(PRODUCTS_FILE, [])
orders = load_json(ORDERS_FILE, [])

# ------------------------ BOT SETUP ------------------------

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

builder = InlineKeyboardBuilder()
builder.row(InlineKeyboardButton(text="Browse Products", callback_data="browse"))
builder.row(InlineKeyboardButton(text="My Orders", callback_data="orders"))
builder.row(InlineKeyboardButton(text="Support", callback_data="support"))
main_kb = builder.as_markup()

back_kb_builder = InlineKeyboardBuilder()
back_kb_builder.row(InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="continue"))
back_kb = back_kb_builder.as_markup()

continue_kb_builder = InlineKeyboardBuilder()
continue_kb_builder.row(InlineKeyboardButton(text="Continue", callback_data="continue"))
continue_kb = continue_kb_builder.as_markup()

# ------------------------ SAVE ALL ------------------------

def save_all():
    save_json(USERS_FILE, users)
    save_json(PRODUCTS_FILE, products)
    save_json(ORDERS_FILE, orders)

# ------------------------ START ------------------------

@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    uid = msg.from_user.id
    if uid not in users:
        users.append(uid)
        save_all()

    # Silently remove the old reply keyboard by sending and deleting a temporary message
    temp_msg = await msg.answer(".", reply_markup=ReplyKeyboardRemove())
    await temp_msg.delete()

    await msg.answer_photo(
        photo="https://i.ibb.co/gbmLTFkg/20251119-185606.jpg",
        caption="<b>Welcome to our official bot. Get secure accounts services, fast order confirmation, reliable communication, and trusted support for all your professional needs.</b>\n\n"
                "Tap the <b>Continue</b> button below to access the menu and start your journey with our premium services.",
        reply_markup=continue_kb
    )

# ------------------------ BROWSE PRODUCTS ------------------------

@dp.callback_query(F.data == "browse")
async def browse(callback: types.CallbackQuery):
    if not products:
        return await callback.message.edit_text("<b>We're sorry, but there are no products available at the moment.</b>", reply_markup=back_kb)

    text = "<b>🛍️ Available Products</b>\n\n"
    for p in products:
        text += f"<b>ID:</b> {p['id']} | <b>{p['name']}</b> | <b>Price:</b> ₹{p['price']}\n"
    text += "\nTo place an order, please use the format: <code>/order &lt;product_id&gt; &lt;quantity&gt;</code>"

    await callback.message.edit_text(text, reply_markup=back_kb)

# ------------------------ ORDER CREATION ------------------------

@dp.message(Command("order"))
async def order_cmd(msg: types.Message):
    try:
        _, pid, qty = msg.text.split()
        pid = int(pid)
        qty = int(qty)
    except:
        return await msg.reply("<b>Invalid Format</b>\n\nPlease use the format: <code>/order &lt;product_id&gt; &lt;quantity&gt;</code>")

    product = next((p for p in products if p["id"] == pid), None)
    if not product:
        return await msg.reply("<b>Product Not Found</b>\n\nPlease enter a valid product ID.")

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
        f"<b>✅ Order Created Successfully!</b>\n\n"
        f"<b>Order ID:</b> <code>{order_id}</code>\n"
        f"<b>Total Amount:</b> ₹{amount}\n\n"
        "To complete your order, please send the payment and then reply with the following message, attaching a screenshot:\n"
        f"<code>PAYMENT {order_id}</code>"
    )
    await msg.reply(pay_text)

    # Notify admin
    await bot.send_message(ADMIN_ID, f"<b>New Order Alert!</b>\n\nOrder <code>{order_id}</code> was placed by user <code>{msg.from_user.id}</code>.")

# ------------------------ PAYMENT CONFIRMATION ------------------------

@dp.message(F.text.startswith("PAYMENT"))
async def handle_payment(msg: types.Message):
    try:
        _, oid = msg.text.split()
        oid = int(oid)
    except:
        return await msg.reply("<b>Invalid Format</b>\n\nPlease use the format: <code>PAYMENT &lt;order_id&gt;</code>")

    order = next((o for o in orders if o["id"] == oid), None)
    if not order:
        return await msg.reply("<b>Order Not Found</b>\n\nPlease enter a valid order ID.")

    order["status"] = "paid"
    order["confirmed_at"] = str(datetime.now())
    save_all()

    # User message
    await msg.reply(
        "<b>✅ Payment Received!</b>\n\n"
        "Thank you for your order! Our team will contact you shortly to arrange for delivery."
    )

    # Admin message
    await bot.send_message(ADMIN_ID, f"<b>Payment Confirmed!</b>\n\nOrder <code>{oid}</code> has been marked as PAID. Please contact user <code>{order['user']}</code> to arrange delivery.")

# ------------------------ MY ORDERS ------------------------

@dp.callback_query(F.data == "orders")
async def my_orders(callback: types.CallbackQuery):
    my = [o for o in orders if o["user"] == callback.from_user.id]
    if not my:
        return await callback.message.edit_text("<b>You have no orders yet.</b>\n\nFeel free to browse our products!", reply_markup=back_kb)

    text = "<b>📄 Your Order History</b>\n\n"
    for o in my:
        text += f"<b>ID:</b> <code>{o['id']}</code> | <b>Qty:</b> {o['qty']} | <b>Amount:</b> ₹{o['amount']} | <b>Status:</b> {o['status']}\n"

    await callback.message.edit_text(text, reply_markup=back_kb)

# ------------------------ SUPPORT ------------------------

@dp.callback_query(F.data == "support")
async def support_msg(callback: types.CallbackQuery):
    await callback.message.edit_text("<b>Need Help?</b>\n\nIf you have any questions or issues, please describe them in a message. Our admin will get back to you as soon as possible.", reply_markup=back_kb)

@dp.callback_query(F.data == "continue")
async def continue_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "<b>Welcome to the Instagram Supplier Bot!</b>\n\n"
        "Please choose an option from the menu below to get started.",
        reply_markup=main_kb
    )

# ------------------------ BROADCAST ------------------------

@dp.message(Command("broadcast"))
async def admin_broadcast(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

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
        except Exception as e:
            print(f"Error broadcasting to user {uid}: {e}")

    await msg.reply(f"Broadcast sent to {sent}/{len(users)} users.")

# ------------------------ RUN BOT ------------------------

async def main():
    @dp.errors()
    async def error_handler(update, exception):
        print(f"Update {update} caused error: {exception}")

    print("Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())