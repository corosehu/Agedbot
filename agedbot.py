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
    selecting_variants = State()
    entering_quantity = State()
    selecting_payment_method = State()
    uploading_screenshot = State()

class SupportFlow(StatesGroup):
    chatting = State()

class ProductFlow(StatesGroup):
    add_name = State()
    add_variants = State()
    edit_product = State()
    edit_name = State()
    edit_price = State()
    manage_variants = State()
    add_new_variants = State()

BOT_TOKEN = "7848720803:AAG3rU2bRB3BBB6iI0-BNgxqneTO0DU0ewA"
ADMIN_ID = 6675623588
SUPPORT_CHANNEL_ID = -1003397194178

PAYMENT_DETAILS = {
    "BTC": {"name": "BTC", "address": "14nfbfY9D2qoLXTCkwZLcREBREMFcZsTq3", "symbol": "₿"},
    "USDT_TRC20": {"name": "USDT (TRC20)", "address": "TLWDLpoGRW8fiN1ZMBbme39PKZLmJovh18", "symbol": "𝕌"},
    "ETH_ERC20": {"name": "ETH (ERC20)", "address": "0x24d8137da5d423e3e70e48904f8b9396aa7a9a53", "symbol": "Ξ"},
    "USDC_BEP20": {"name": "USDC (BEP20)", "address": "0x24d8137da5d423e3e70e48904f8b9396aa7a9a53", "symbol": "🔵"},
    "SOL": {"name": "SOL", "address": "GHLNb3emz3ZStaC2iir6wVQU51SaEkurkfDuTycmdiMB", "symbol": "🪐"},
    "Binance_ID": {"name": "Binance ID", "address": "1083136815", "symbol": "🏦"}
}

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
        return default
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if path == PRODUCTS_FILE:
            migrated = False
            for p in data:
                # Remove obsolete top-level price
                if "price" in p:
                    del p["price"]
                    migrated = True

                # Migrate string variants to objects with default price 0.0
                if "variants" in p and isinstance(p.get("variants"), list):
                    if p["variants"] and isinstance(p["variants"][0], str):
                        p["variants"] = [{"name": v, "enabled": True, "price": 0.0} for v in p["variants"]]
                        migrated = True

            if migrated:
                save_json(path, data)
        return data

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

        # Notify channel about new user
        user = msg.from_user
        username = f"@{user.username}" if user.username else "N/A"
        notification_text = (
            f"🆕 <b>New User Started Bot</b>\n\n"
            f"<b>Name:</b> <a href=\"tg://user?id={user.id}\">{user.full_name}</a>\n"
            f"<b>Username:</b> {username}\n"
            f"<b>User ID:</b> <code>{user.id}</code>\n"
            f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        try:
            await bot.send_message(SUPPORT_CHANNEL_ID, notification_text)
        except Exception as e:
            print(f"Failed to send new user notification: {e}")

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
        product_kb.row(InlineKeyboardButton(text=f"✅ {p['name']}", callback_data=f"select_prod_{p['id']}"))
    product_kb.row(InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="continue"))

    await callback.message.edit_text("<b>🛍️ Available Products</b>\n\nPlease select a product from the list below:", reply_markup=product_kb.as_markup())
    await state.set_state(OrderFlow.selecting_product)


@dp.callback_query(OrderFlow.selecting_product, F.data.startswith("select_prod_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = next((p for p in products if p["id"] == product_id), None)

    if "variants" in product and any(v.get("enabled", False) for v in product["variants"]):
        await state.update_data(product_id=product_id, selected_variants=[])

        variants_kb = InlineKeyboardBuilder()
        for i, variant in enumerate(product["variants"]):
            if variant.get("enabled", False):
                price_text = f" - ${variant.get('price', 0.0)}"
                variants_kb.row(InlineKeyboardButton(
                    text=f"☐ {variant['name']}{price_text}",
                    callback_data=f"select_variant_{i}"
                ))
        variants_kb.row(InlineKeyboardButton(text="➡️ Done (No variants selected)", callback_data="done_selecting_variants"))

        await callback.message.edit_text(
            f"<b>{product['name']}</b>\n\n"
            "Please select one or more options. The final price will be based on the most expensive variant you choose.\n\n"
            "<b>Current Price per item: $0.0</b>",
            reply_markup=variants_kb.as_markup()
        )
        await state.set_state(OrderFlow.selecting_variants)
    else:
        # Fallback for products without variants, though the new model discourages this.
        await state.update_data(product_id=product_id, selected_variants=[], unit_price=0.0)
        await callback.message.edit_text("This product has no options. Please enter the quantity you'd like to order:")
        await state.set_state(OrderFlow.entering_quantity)


@dp.callback_query(OrderFlow.selecting_variants, F.data.startswith("select_variant_"))
async def select_variant(callback: types.CallbackQuery, state: FSMContext):
    variant_index = int(callback.data.split("_")[-1])
    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)

    selected_indices = user_data.get("selected_variants", [])
    if variant_index in selected_indices:
        selected_indices.remove(variant_index)
    else:
        selected_indices.append(variant_index)

    selected_prices = [product["variants"][i].get('price', 0.0) for i in selected_indices]
    unit_price = max(selected_prices) if selected_prices else 0.0

    await state.update_data(selected_variants=selected_indices, unit_price=unit_price)

    variants_kb = InlineKeyboardBuilder()
    for i, variant in enumerate(product["variants"]):
        if variant.get("enabled", False):
            price_text = f" - ${variant.get('price', 0.0)}"
            checkbox = "☑️" if i in selected_indices else "☐"
            variants_kb.row(InlineKeyboardButton(
                text=f"{checkbox} {variant['name']}{price_text}",
                callback_data=f"select_variant_{i}"
            ))

    done_text = "➡️ Done"
    if selected_indices:
        done_text += f" (Price: ${unit_price})"
    else:
        done_text += " (No variants selected)"
    variants_kb.row(InlineKeyboardButton(text=done_text, callback_data="done_selecting_variants"))

    await callback.message.edit_text(
        f"<b>{product['name']}</b>\n\n"
        "Please select one or more options. The final price will be based on the most expensive variant you choose.\n\n"
        f"<b>Current Price per item: ${unit_price}</b>",
        reply_markup=variants_kb.as_markup()
    )


@dp.callback_query(OrderFlow.selecting_variants, F.data == "done_selecting_variants")
async def done_selecting_variants(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Please enter the quantity you'd like to order (e.g., 1, 2, 5):")
    await state.set_state(OrderFlow.entering_quantity)


@dp.message(OrderFlow.entering_quantity, F.text)
async def enter_quantity(msg: types.Message, state: FSMContext):
    try:
        qty = float(msg.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        return await msg.reply("<b>Invalid Quantity</b>\n\nPlease enter a valid number (e.g., 1, 2, 5).")

    await state.update_data(quantity=qty)

    payment_kb = InlineKeyboardBuilder()
    for key, details in PAYMENT_DETAILS.items():
        payment_kb.row(InlineKeyboardButton(text=f"{details['symbol']} {details['name']}", callback_data=f"payment_{key}"))
    payment_kb.row(InlineKeyboardButton(text="⬅️ Back to Product Selection", callback_data="browse"))

    user_data = await state.get_data()
    unit_price = user_data.get("unit_price", 0.0)
    total_amount = unit_price * qty
    await state.update_data(total_amount=total_amount)

    await msg.answer(
        f"<b>Total Amount:</b> <b>${total_amount}</b>\n\n"
        "Please select your preferred payment method:",
        reply_markup=payment_kb.as_markup()
    )
    await state.set_state(OrderFlow.selecting_payment_method)


@dp.callback_query(OrderFlow.selecting_payment_method, F.data.startswith("payment_"))
async def select_payment(callback: types.CallbackQuery, state: FSMContext):
    payment_key = callback.data[len("payment_"):]
    payment_info = PAYMENT_DETAILS.get(payment_key)
    if not payment_info:
        return await callback.answer("Invalid payment method selected.", show_alert=True)

    await state.update_data(payment_method=payment_key)
    user_data = await state.get_data()

    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    qty = user_data.get('quantity', 0)
    amount = user_data.get('total_amount', 0.0)
    unit_price = user_data.get('unit_price', 0.0)

    order_id = len(orders) + 1
    new_order = {
        "id": order_id,
        "user": callback.from_user.id,
        "product_id": user_data['product_id'],
        "selected_variants": [product["variants"][i]["name"] for i in user_data.get("selected_variants", [])],
        "qty": qty,
        "unit_price": unit_price,
        "amount": amount,
        "payment_method": payment_key,
        "screenshot_file_id": None,
        "status": "awaiting_screenshot",
        "created": str(datetime.now())
    }
    orders.append(new_order)
    save_all()

    variants_text = ""
    if "selected_variants" in user_data and user_data.get("selected_variants"):
        variants_text = "\n<b>Variants:</b> " + ", ".join([product["variants"][i]["name"] for i in user_data["selected_variants"]])

    summary_text = (
        f"🧾 <b>Order Summary</b>\n\n"
        f"<b>Product:</b> {product['name']}{variants_text}\n"
        f"<b>Quantity:</b> {qty}\n"
        f"<b>Total:</b> ${amount}\n"
        f"<b>Payment Method:</b> {payment_info['name']}\n\n"
        f"✅ <b>To complete payment, please send ${amount} to the address below:</b>\n"
        f"<code>{payment_info['address']}</code>\n\n"
        f"After sending, <b>reply to this message with your payment screenshot.</b>\n\n"
        f"⏳ <b>Note:</b> Your order will be processed manually after admin verification. You’ll receive a notification once confirmed.\n"
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
    order["status"] = "pending_confirmation"
    save_all()

    await msg.reply("<b>Screenshot received.</b> Your order is now pending admin confirmation.")

    product = next((p for p in products if p["id"] == order['product_id']), None)
    variants_text = ""
    if "selected_variants" in order and order["selected_variants"]:
        variants_text = "\n<b>Variants:</b> " + ", ".join(order["selected_variants"])

    admin_notification = (
        f"🆕 <b>New Order Received</b>\n\n"
        f"<b>Order ID:</b> #{order['id']}\n"
        f"<b>User:</b> <a href=\"tg://user?id={order['user']}\">{order['user']}</a>\n"
        f"<b>Product:</b> {product['name']}{variants_text}\n"
        f"<b>Quantity:</b> {order['qty']}\n"
        f"<b>Total:</b> ${order['amount']}\n"
        f"<b>Status:</b> ⏳ Pending Confirmation\n\n"
        f"<i>Click below to confirm or reject this order.</i>"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_order_{order['id']}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_order_{order['id']}")
    )

    try:
        sent_msg = await bot.send_photo(SUPPORT_CHANNEL_ID, order["screenshot_file_id"], caption=admin_notification, reply_markup=kb.as_markup())
        order["channel_msg_id"] = sent_msg.message_id
        save_all()
    except Exception as e:
        print(f"Failed to send order notification to channel: {e}")

    await state.clear()

@dp.callback_query(F.data.startswith("confirm_order_"))
async def confirm_order_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
         return await callback.answer("You are not authorized.", show_alert=True)

    order_id = int(callback.data.split("_")[-1])
    order = next((o for o in orders if o["id"] == order_id), None)

    if not order:
        return await callback.answer("Order not found.", show_alert=True)

    if order["status"] != "pending_confirmation":
         return await callback.answer("Order already processed.", show_alert=True)

    order["status"] = "confirmed"
    save_all()

    # Notify User
    try:
        await bot.send_message(order["user"], "✅ <b>Order Confirmed!</b>\n\nOur team will contact you shortly for delivery. Thank you!")
    except Exception as e:
        print(f"Failed to notify user {order['user']}: {e}")

    # Update Channel Message
    try:
        product = next((p for p in products if p["id"] == order['product_id']), None)
        variants_text = ""
        if "selected_variants" in order and order["selected_variants"]:
            variants_text = "\n<b>Variants:</b> " + ", ".join(order["selected_variants"])

        new_caption = (
            f"🆕 <b>New Order Received</b>\n\n"
            f"<b>Order ID:</b> #{order['id']}\n"
            f"<b>User:</b> <a href=\"tg://user?id={order['user']}\">{order['user']}</a>\n"
            f"<b>Product:</b> {product['name']}{variants_text}\n"
            f"<b>Quantity:</b> {order['qty']}\n"
            f"<b>Total:</b> ${order['amount']}\n"
            f"<b>Status:</b> ✅ CONFIRMED – Notified user"
        )

        await bot.edit_message_caption(
            chat_id=SUPPORT_CHANNEL_ID,
            message_id=callback.message.message_id,
            caption=new_caption,
            reply_markup=None
        )
    except Exception as e:
        print(f"Failed to update channel message: {e}")

    await callback.answer("Order Confirmed")

@dp.callback_query(F.data.startswith("reject_order_"))
async def reject_order_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
         return await callback.answer("You are not authorized.", show_alert=True)

    order_id = int(callback.data.split("_")[-1])
    order = next((o for o in orders if o["id"] == order_id), None)

    if not order:
        return await callback.answer("Order not found.", show_alert=True)

    if order["status"] != "pending_confirmation":
         return await callback.answer("Order already processed.", show_alert=True)

    order["status"] = "rejected"
    save_all()

    # Notify User
    try:
        await bot.send_message(order["user"], "❌ <b>Order Rejected</b>\n\nWe're sorry, but your order could not be processed. Please contact support for details.")
    except Exception as e:
        print(f"Failed to notify user {order['user']}: {e}")

    # Update Channel Message
    try:
        product = next((p for p in products if p["id"] == order['product_id']), None)
        variants_text = ""
        if "selected_variants" in order and order["selected_variants"]:
            variants_text = "\n<b>Variants:</b> " + ", ".join(order["selected_variants"])

        new_caption = (
            f"🆕 <b>New Order Received</b>\n\n"
            f"<b>Order ID:</b> #{order['id']}\n"
            f"<b>User:</b> <a href=\"tg://user?id={order['user']}\">{order['user']}</a>\n"
            f"<b>Product:</b> {product['name']}{variants_text}\n"
            f"<b>Quantity:</b> {order['qty']}\n"
            f"<b>Total:</b> ${order['amount']}\n"
            f"<b>Status:</b> ❌ REJECTED – User notified"
        )

        await bot.edit_message_caption(
            chat_id=SUPPORT_CHANNEL_ID,
            message_id=callback.message.message_id,
            caption=new_caption,
            reply_markup=None
        )
    except Exception as e:
        print(f"Failed to update channel message: {e}")

    await callback.answer("Order Rejected")

# ------------------------ PRODUCT MANAGEMENT ------------------------

@dp.message(Command("manageproduct"), F.from_user.id == ADMIN_ID)
async def manage_product(msg: types.Message):
    manage_kb = InlineKeyboardBuilder()
    manage_kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data="add_product"))
    manage_kb.row(InlineKeyboardButton(text="✏️ Edit Product", callback_data="edit_product_list"))
    manage_kb.row(InlineKeyboardButton(text="⬅️ Back", callback_data="continue"))
    await msg.answer("📦 Welcome to the Product Management Panel. Please choose an option:", reply_markup=manage_kb.as_markup())


@dp.callback_query(F.data == "add_product")
async def add_product_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Enter product name (e.g., Instagram Aged):")
    await state.set_state(ProductFlow.add_name)


@dp.message(ProductFlow.add_name, F.text)
async def add_product_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer(
        "Enter variants in the format:\n"
        "<code>\"VariantName1+Price1\"/\"VariantName2+Price2\"</code>\n\n"
        "For example: <code>\"Normal Aged+1.5\"/\"2FA+2\"</code>\n"
        "Reply with `none` if there are no variants."
    )
    await state.set_state(ProductFlow.add_variants)


@dp.message(ProductFlow.add_variants, F.text)
async def add_product_variants(msg: types.Message, state: FSMContext):
    variants = []
    if msg.text.lower() != "none":
        try:
            parts = [v.strip() for v in msg.text.strip('"').split('"/"')]
            for part in parts:
                if "+" in part:
                    name, price_str = part.rsplit("+", 1)
                    price = float(price_str)
                else:
                    name, price = part, 0.0
                variants.append({"name": name.strip(), "enabled": True, "price": price})
        except (ValueError, IndexError):
            return await msg.reply(
                "<b>Invalid Format.</b>\n"
                "Please use the format: <code>\"Name1+Price1\"/\"Name2+Price2\"</code>"
            )

    user_data = await state.get_data()
    new_product = {
        "id": len(products) + 1,
        "name": user_data['name'],
        "variants": variants
    }
    products.append(new_product)
    save_all()
    await msg.answer("✅ <b>Product added successfully!</b>")
    await state.clear()


@dp.callback_query(F.data == "edit_product_list")
async def edit_product_list(callback: types.CallbackQuery):
    if not products:
        return await callback.message.edit_text("<b>No products to edit.</b>", reply_markup=back_kb)

    edit_kb = InlineKeyboardBuilder()
    for p in products:
        edit_kb.row(InlineKeyboardButton(text=f"✏️ {p['name']}", callback_data=f"edit_prod_{p['id']}"))
    edit_kb.row(InlineKeyboardButton(text="⬅️ Back", callback_data="manage_product_main"))
    await callback.message.edit_text("Select a product to edit:", reply_markup=edit_kb.as_markup())


@dp.callback_query(F.data.startswith("edit_prod_"))
async def edit_product_menu(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return await callback.answer("Product not found.", show_alert=True)

    await state.update_data(product_id=product_id)

    edit_options_kb = InlineKeyboardBuilder()
    edit_options_kb.row(InlineKeyboardButton(text="✏️ Edit Name", callback_data="edit_name"))
    edit_options_kb.row(InlineKeyboardButton(text="🎛️ Manage Variants", callback_data="manage_variants"))
    edit_options_kb.row(InlineKeyboardButton(text="🗑️ Delete Product", callback_data="delete_product"))
    edit_options_kb.row(InlineKeyboardButton(text="⬅️ Back to Product List", callback_data="edit_product_list"))

    await callback.message.edit_text(
        f"<b>Editing Product:</b> {product['name']}\n\n"
        f"Please choose an option to edit:",
        reply_markup=edit_options_kb.as_markup()
    )
    await state.set_state(ProductFlow.edit_product)


@dp.callback_query(ProductFlow.edit_product, F.data == "edit_name")
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Enter the new product name:")
    await state.set_state(ProductFlow.edit_name)


@dp.message(ProductFlow.edit_name, F.text)
async def edit_name_finish(msg: types.Message, state: FSMContext):
    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    product['name'] = msg.text
    save_all()
    await msg.answer("✅ <b>Name updated successfully!</b>")
    await state.clear()




@dp.callback_query(ProductFlow.edit_product, F.data == "delete_product")
async def delete_product(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    products[:] = [p for p in products if p["id"] != user_data['product_id']]
    save_all()
    await callback.message.edit_text("🗑️ <b>Product deleted successfully!</b>")
    await state.clear()


@dp.callback_query(ProductFlow.edit_product, F.data == "manage_variants")
async def manage_variants_menu(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)

    variants_kb = InlineKeyboardBuilder()
    if "variants" in product and product["variants"]:
        for i, variant in enumerate(product["variants"]):
            status_icon = "✅" if variant["enabled"] else "❌"
            price_text = f" - ${variant.get('price', 0.0)}"
            variants_kb.row(
                InlineKeyboardButton(text=f"{status_icon} {variant['name']}{price_text}", callback_data=f"toggle_variant_{i}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"remove_variant_{i}")
            )
    variants_kb.row(InlineKeyboardButton(text="➕ Add New Variants", callback_data="add_new_variants"))
    variants_kb.row(InlineKeyboardButton(text="⬅️ Back to Edit Menu", callback_data=f"edit_prod_{product['id']}"))

    await callback.message.edit_text(
        f"<b>Managing Variants for:</b> {product['name']}",
        reply_markup=variants_kb.as_markup()
    )
    await state.set_state(ProductFlow.manage_variants)


@dp.callback_query(ProductFlow.manage_variants, F.data.startswith("toggle_variant_"))
async def toggle_variant(callback: types.CallbackQuery, state: FSMContext):
    variant_index = int(callback.data.split("_")[-1])
    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    product["variants"][variant_index]["enabled"] = not product["variants"][variant_index]["enabled"]
    save_all()
    await manage_variants_menu(callback, state)


@dp.callback_query(ProductFlow.manage_variants, F.data.startswith("remove_variant_"))
async def remove_variant(callback: types.CallbackQuery, state: FSMContext):
    variant_index = int(callback.data.split("_")[-1])
    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    product["variants"].pop(variant_index)
    save_all()
    await manage_variants_menu(callback, state)


@dp.callback_query(ProductFlow.manage_variants, F.data == "add_new_variants")
async def add_new_variants_start(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    back_kb = InlineKeyboardBuilder()
    back_kb.row(InlineKeyboardButton(text="⬅️ Back", callback_data=f"edit_prod_{product['id']}"))
    await callback.message.edit_text(
        "Send new variants in the format:\n"
        "<code>\"VariantName1+Price1\"/\"VariantName2+Price2\"</code>",
        reply_markup=back_kb.as_markup()
    )
    await state.set_state(ProductFlow.add_new_variants)


@dp.message(ProductFlow.add_new_variants, F.text)
async def add_new_variants_finish(msg: types.Message, state: FSMContext):
    try:
        parts = [v.strip() for v in msg.text.strip('"').split('"/"')]
        new_variants = []
        for part in parts:
            if "+" in part:
                name, price_str = part.rsplit("+", 1)
                price = float(price_str)
            else:
                name, price = part, 0.0
            new_variants.append({"name": name.strip(), "enabled": True, "price": price})
    except (ValueError, IndexError):
        return await msg.reply(
            "<b>Invalid Format.</b>\n"
            "Please use the format: <code>\"Name1+Price1\"/\"Name2+Price2\"</code>"
        )

    user_data = await state.get_data()
    product = next((p for p in products if p["id"] == user_data['product_id']), None)
    if "variants" not in product:
        product["variants"] = []
    product["variants"].extend(new_variants)
    save_all()
    await msg.answer("✅ <b>New variants added successfully!</b>")

    # After adding, just go back to the menu, don't try to rebuild the keyboard here.
    # Let the user navigate back naturally.
    await state.set_state(ProductFlow.edit_product)

# ------------------------ MY ORDERS ------------------------

# ------------------------ MY ORDERS ------------------------

@dp.callback_query(F.data == "orders")
async def my_orders(callback: types.CallbackQuery):
    my = [o for o in orders if o["user"] == callback.from_user.id]
    if not my:
        return await callback.message.edit_text("<b>You have no orders yet.</b>\n\nFeel free to browse our products!", reply_markup=back_kb)

    text = "<b>📄 Your Order History</b>\n\n"
    for o in my:
        text += f"<b>ID:</b> <code>{o['id']}</code> | <b>Qty:</b> {o['qty']} | <b>Amount:</b> ${o['amount']} | <b>Status:</b> {o['status']}\n"

    await callback.message.edit_text(text, reply_markup=back_kb)

# ------------------------ SUPPORT ------------------------

@dp.callback_query(F.data == "support")
async def support_msg(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("<b>Need Help?</b>\n\nIf you have any questions or issues, please describe them in a message. Our admin will get back to you as soon as possible.", reply_markup=back_kb)
    await state.set_state(SupportFlow.chatting)

@dp.message(SupportFlow.chatting)
async def support_forward(msg: types.Message):
    user = msg.from_user
    username = f"@{user.username}" if user.username else "N/A"

    issue_text = msg.text or msg.caption or "[Media Message]"

    notification_text = (
        f"📩 <b>New Support Request</b>\n\n"
        f"<b>Name:</b> <a href=\"tg://user?id={user.id}\">{user.full_name}</a>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>User ID:</b> <code>{user.id}</code>\n\n"
        f"<b>User Support Issue:</b>\n{issue_text}"
    )

    try:
        if msg.photo:
            await bot.send_photo(SUPPORT_CHANNEL_ID, msg.photo[-1].file_id, caption=notification_text)
        else:
            await bot.send_message(SUPPORT_CHANNEL_ID, notification_text)

        await msg.reply("✅ <b>Your support request has been sent to the admin team.</b>\n\nWe will contact you shortly.")
    except Exception as e:
        print(f"Failed to forward message to support channel: {e}")
        await msg.reply("❌ <b>Error sending request.</b> Please try again later.")

@dp.callback_query(F.data == "continue")
async def continue_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
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