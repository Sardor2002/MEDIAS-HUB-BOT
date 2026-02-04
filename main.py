import asyncio
import os
import json
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# =============================
# CONFIG
# =============================
BOT_TOKEN = "8109609846:AAFb9vrMlzwRSOjb5l4HOHrITd8A3sPyszA"
ADMIN_ID = 7764313855
# Barqaror yuklash API manzili
API_URL = "https://api.vkrdownloader.com/server?vkr="

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
FORCE_FILE = os.path.join(BASE_DIR, "force.json")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =============================
# STORAGE & DATA MGR
# =============================
user_links = {}
admin_waiting_broadcast = set()
admin_selected_users = {}
admin_waiting_force = set()

def load_data(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_data(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

users_data = load_data(USERS_FILE)
force_join_list = load_data(FORCE_FILE)

# =============================
# MAJBURIY OBUNA TEKSHIRUVI
# =============================
async def check_sub(user_id):
    if not force_join_list: return True
    for channel_id in force_join_list:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ["left", "kicked"]: return False
        except: continue
    return True

# =============================
# BOT HANDLERLARI
# =============================

@dp.message(CommandStart())
async def start(message: types.Message):
    uid = str(message.from_user.id)
    if uid not in users_data:
        users_data[uid] = {"username": message.from_user.username, "first_name": message.from_user.first_name}
        save_data(USERS_FILE, users_data)

    if not await check_sub(message.from_user.id):
        kb = []
        for fid, info in force_join_list.items():
            kb.append([InlineKeyboardButton(text=info['name'], url=f"https://t.me/{info['name'].replace('@','')}")])
        kb.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        return await message.answer("❌ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    await message.answer("🎬 *Xush kelibsiz! Video linkini yuboring:*", parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Rahmat! Endi link yuborishingiz mumkin.")
    else:
        await call.answer("❌ Hali a'zo emassiz!", show_alert=True)

@dp.message(F.text.startswith("http"))
async def handle_link(message: types.Message):
    if not await check_sub(message.from_user.id): return
    
    uid = message.from_user.id
    user_links[uid] = message.text.strip()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Video", callback_data="type_video"),
         InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data="type_audio")]
    ])
    await message.answer(f"⬇️ *Formatni tanlang:* \n`{user_links[uid]}`", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.in_(["type_video", "type_audio"]))
async def process_download(call: types.CallbackQuery):
    is_audio = call.data == "type_audio"
    url = user_links.get(call.from_user.id)
    
    if not url: return await call.answer("❌ Xato: Link topilmadi!")

    status_msg = await call.message.edit_text("⏳ *Yuklanmoqda...*", parse_mode="Markdown")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}{url}") as resp:
                data = await resp.json()
                # API dan kelgan birinchi linkni olish
                media_url = data['data']['downloads'][0]['url']
                
                if is_audio:
                    await call.message.answer_audio(media_url, caption="✅ Audio yuklandi!")
                else:
                    await call.message.answer_video(media_url, caption="✅ Video yuklandi!")
                
                await status_msg.delete()
    except Exception as e:
        logging.error(f"Download error: {e}")
        await status_msg.edit_text("❌ Xatolik: Video yuklab bo'lmadi. Link noto'g'ri bo'lishi mumkin.")

# =============================
# ADMIN PANEL (SIZNING ASLIY KODINGIZ)
# =============================
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm_users")],
        [InlineKeyboardButton(text="📌 Majburiy obuna", callback_data="adm_force")],
        [InlineKeyboardButton(text="◀️ Chiqish", callback_data="adm_exit")]
    ])

@dp.message(F.text == "/admin")
async def admin_main(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🛠 *Admin Panel*", reply_markup=get_admin_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "adm_stats")
async def adm_stats(call: types.CallbackQuery):
    await call.answer(f"📊 Jami a'zolar: {len(users_data)}", show_alert=True)

@dp.callback_query(F.data == "adm_users")
async def list_users(call: types.CallbackQuery):
    kb = []
    sel = admin_selected_users.get(call.from_user.id, set())
    # Faqat oxirgi 20ta foydalanuvchini chiqarish (xotira uchun)
    for uid, data in list(users_data.items())[-20:]:
        status = "✅" if uid in sel else "👤"
        row = [
            InlineKeyboardButton(text="🔗", url=f"https://t.me/{data.get('username')}") if data.get('username') else InlineKeyboardButton(text="🆔", callback_data=f"info_{uid}"),
            InlineKeyboardButton(text=f"{status} {data['first_name']}", callback_data=f"toggle_{uid}"),
            InlineKeyboardButton(text="🗑", callback_data=f"del_{uid}")
        ]
        kb.append(row)
    kb.append([InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="send_bc")])
    kb.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back")])
    await call.message.edit_text("👥 *Foydalanuvchilar (Oxirgi 20ta):*", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle(call: types.CallbackQuery):
    uid = call.data.split("_")[1]
    admin_id = call.from_user.id
    if admin_id not in admin_selected_users: admin_selected_users[admin_id] = set()
    if uid in admin_selected_users[admin_id]: admin_selected_users[admin_id].remove(uid)
    else: admin_selected_users[admin_id].add(uid)
    await list_users(call)

@dp.callback_query(F.data.startswith("del_"))
async def delete_u(call: types.CallbackQuery):
    uid = call.data.split("_")[1]
    if uid in users_data: del users_data[uid]
    save_data(USERS_FILE, users_data)
    await list_users(call)

@dp.message(lambda m: m.from_user.id in admin_waiting_broadcast)
async def bc_logic(message: types.Message):
    admin_id = message.from_user.id
    admin_waiting_broadcast.remove(admin_id)
    targets = admin_selected_users.get(admin_id, users_data.keys())
    sent = 0
    for uid in targets:
        try:
            await message.copy_to(uid)
            sent += 1
            await asyncio.sleep(0.1)
        except: continue
    await message.answer(f"✅ {sent} kishiga yuborildi.")
    admin_selected_users[admin_id] = set()

@dp.callback_query(F.data == "send_bc")
async def bc_start(call: types.CallbackQuery):
    admin_waiting_broadcast.add(call.from_user.id)
    await call.message.answer("⌨️ Xabar matnini yuboring:")

@dp.callback_query(F.data == "adm_force")
async def force_menu(call: types.CallbackQuery):
    kb = []
    for fid, info in force_join_list.items():
        kb.append([InlineKeyboardButton(text=f"❌ {info['name']}", callback_data=f"remove_f_{fid}")])
    kb.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_f")])
    kb.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_back")])
    await call.message.edit_text("📌 *Majburiy obuna kanallari:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data == "add_f")
async def add_f_start(call: types.CallbackQuery):
    admin_waiting_force.add(call.from_user.id)
    await call.message.answer("📌 Format: `ID,USERNAME` (Masalan: `-100123,@kanal`)")

@dp.message(lambda m: m.from_user.id in admin_waiting_force)
async def add_f_logic(message: types.Message):
    admin_waiting_force.remove(message.from_user.id)
    try:
        fid, name = message.text.split(",")
        force_join_list[fid.strip()] = {"name": name.strip()}
        save_data(FORCE_FILE, force_join_list)
        await message.answer("✅ Kanal qo'shildi.")
    except: await message.answer("❌ Xato format!")

@dp.callback_query(F.data.startswith("remove_f_"))
async def remove_f(call: types.CallbackQuery):
    fid = call.data.replace("remove_f_", "")
    if fid in force_join_list: del force_join_list[fid]
    save_data(FORCE_FILE, force_join_list)
    await force_menu(call)

@dp.callback_query(F.data == "adm_back")
async def adm_back(call: types.CallbackQuery):
    await call.message.edit_text("🛠 *Admin Panel*", reply_markup=get_admin_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "adm_exit")
async def adm_exit(call: types.CallbackQuery):
    await call.message.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())