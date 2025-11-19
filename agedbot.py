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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

class OrderFlow(StatesGroup):
    selecting_product = State()
    entering_quantity = State()
    selecting_payment_method = State()
    uploading_screenshot = State()

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
    temp_msg = await msg.answer("...", reply_markup=ReplyKeyboardRemove())
    await temp_msg.delete()

    await msg.answer_photo(
        photo="https://i.ibb.co/gbmLTFkg/20251119-185606.jpg",
        caption="<b>Welcome to our official bot. Get secure accounts services, fast order confirmation, reliable communication, and trusted support for all your professional needs.</b>\n\n"
                "Tap the <b>Continue</b> button below to access the menu and start your journey with our premium services.",
        reply_markup=continue_kb
    )

# ------------------------ BROWSE PRODUCTS ------------------------

@dp.callback_query(F.data == "browse")
async def browse(callback: types.CallbackQuery, state: FSMContext):
    if not products:
        return await callback.message.edit_text("<b>We're sorry, but there are no products available at the moment.</b>", reply_markup=back_kb)

    product_kb = InlineKeyboardBuilder()
    for p in products:
        product_kb.row(InlineKeyboardButton(text=f"✅ {p['name']} – ₹{p['price']}", callback_data=f"select_prod_{p['id']}"))
    product_kb.row(InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="continue"))

    await callback.message.edit_text("<b>🛍️ Available Products</b>\n\nPlease select a product from the list below:", reply_markup=product_kb.as_markup())
    await state.set_state(OrderFlow.selecting_product)


@dp.callback_query(OrderFlow.selecting_product, F.data.startswith("select_prod_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    await state.update_data(product_id=product_id)
    await callback.message.edit_text("Please enter the quantity you'd like to order (e.g., 1, 2, 5):")
    await state.set_state(OrderFlow.entering_quantity)


@dp.message(OrderFlow.entering_quantity, F.text)
async def enter_quantity(msg: types.Message, state: FSMContext):
    try:
        qty = int(msg.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        return await msg.reply("<b>Invalid Quantity</b>\n\nPlease enter a valid number (e.g., 1, 2, 5).")

    await state.update_data(quantity=qty)

    payment_kb = InlineKeyboardBuilder()
    payment_methods = ["BTC", "ETH", "USDT (TRC20)", "USDC", "SOL", "Binance ID"]
    symbols = ["₿", "Ξ", "𝕌", "🔵", "🪐", "🏦"]
    for i, method in enumerate(payment_methods):
        payment_kb.row(InlineKeyboardButton(text=f"{symbols[i]} {method}", callback_data=f"payment_{method}"))
    payment_kb.row(InlineKeyboardButton(text="⬅️ Back to Product Selection", callback_data="browse"))

    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    total_amount = product['price'] * qty

    await msg.answer(
        f"<b>Total Amount:</b> <b>₹{total_amount}</b>\n\n"
        "Please select your preferred payment method:",
        reply_markup=payment_kb.as_markup()
    )
    await state.set_state(OrderFlow.selecting_payment_method)


@dp.callback_query(OrderFlow.selecting_payment_method, F.data.startswith("payment_"))
async def select_payment(callback: types.CallbackQuery, state: FSMContext):
    payment_method = callback.data.split("_")[-1]
    await state.update_data(payment_method=payment_method)
    user_data = await state.get_data()

    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    qty = user_data['quantity']
    amount = product['price'] * qty

    order_id = len(orders) + 1
    new_order = {
        "id": order_id,
        "user": callback.from_user.id,
        "product_id": user_data['product_id'],
        "qty": qty,
        "amount": amount,
        "payment_method": payment_method,
        "screenshot_file_id": None,
        "status": "awaiting_screenshot",
        "created": str(datetime.now())
    }
    orders.append(new_order)
    save_all()

    summary_text = (
        f"🧾 <b>Order Summary</b>\n\n"
        f"<b>Product:</b> {product['name']}\n"
        f"<b>Quantity:</b> {qty}\n"
        f"<b>Total:</b> ₹{amount}\n"
        f"<b>Payment Method:</b> {payment_method}\n\n"
        f"✅ <b>To complete payment:</b>\n"
        f"1. Send exact amount to our wallet (we’ll share after confirmation)\n"
        f"2. <b>Reply to this message with your payment screenshot</b>\n\n"
        f"⏳ <b>Note:</b> Your order will be processed manually after admin verification. You’ll receive a notification once confirmed. Our team will contact you directly for delivery.\n"
        f"🕒 <i>Estimated processing: 5–30 mins after payment</i>"
    )

    await callback.message.edit_text(summary_text)
    await state.set_state(OrderFlow.uploading_screenshot)


@dp.message(OrderFlow.uploading_screenshot, F.photo)
async def upload_screenshot(msg: types.Message, state: FSMContext):
    user_orders = [o for o in orders if o["user"] == msg.from_user.id and o["status"] == "awaiting_screenshot"]
    if not user_orders:
        return await msg.reply("<b>Error:</b> No pending order found to attach this screenshot to.")

    order = user_orders[-1]
    order["screenshot_file_id"] = msg.photo[-1].file_id
    order["status"] = "payment_submitted"
    save_all()

    await msg.reply("<b>Screenshot received.</b> Your order is now pending admin confirmation.")

    product = next((p for p in products if p["id"] == order['product_id']), None)
    admin_notification = (
        f"<b>New Payment Submitted!</b>\n\n"
        f"<b>Order ID:</b> <code>{order['id']}</code>\n"
        f"<b>User ID:</b> <code>{order['user']}</code>\n"
        f"<b>Product:</b> {product['name']}\n"
        f"<b>Quantity:</b> {order['qty']}\n"
        f"<b>Amount:</b> ₹{order['amount']}\n"
        f"<b>Payment Method:</b> {order['payment_method']}\n\n"
        f"Please verify the payment and confirm the order with: <code>/confirm {order['id']}</code>"
    )
    await bot.send_photo(ADMIN_ID, order["screenshot_file_id"], caption=admin_notification)
    await state.clear()


@dp.message(Command("confirm"), F.from_user.id == ADMIN_ID)
async def confirm_order(msg: types.Message):
    try:
        _, order_id = msg.text.split()
        order_id = int(order_id)
    except ValueError:
        return await msg.reply("<b>Invalid Format.</b>\n\nPlease use: <code>/confirm &lt;order_id&gt;</code>")

    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return await msg.reply("<b>Order not found.</b>")

    order["status"] = "confirmed"
    save_all()

    await bot.send_message(order["user"], "✅ <b>Order Confirmed!</b>\n\nOur team will contact you shortly on Telegram for delivery. Thank you!")
    await msg.reply(f"Order <code>{order_id}</code> has been confirmed. User notified.")

# ------------------------ MY ORDERS ------------------------

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
    await callback.message.delete()
    await callback.message.answer(
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