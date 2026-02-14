import telebot
import yt_dlp
import os
import re
import json
import logging
import time
from datetime import datetime
from urllib.parse import urlparse
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен из переменных Render (НЕ ХАРДКОД!)
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8575146865'))
bot = telebot.TeleBot(TOKEN)

# Persistent storage для Render
DATA_DIR = os.environ.get('DATA_DIR', './data')
os.makedirs(f'{DATA_DIR}/downloads/video', exist_ok=True)
os.makedirs(f'{DATA_DIR}/downloads/audio', exist_ok=True)

CHANNELS_FILE = f'{DATA_DIR}/channels.json'
USERS_FILE = f'{DATA_DIR}/users.json'

# Загрузка данных
def load_channels():
    try:
        with open(CHANNELS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_channels(channels):
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(channels, f)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

channels = load_channels()
users = load_users()

# Проверка подписки
def check_subscription(user_id, chat_id):
    unsubscribed = []
    for channel in channels:
        try:
            member = bot.get_chat_member(channel['chat_id'], user_id)
            if member.status in ['left', 'kicked']:
                unsubscribed.append(channel)
        except:
            unsubscribed.append(channel)
    return unsubscribed

# МЕНЮ
main_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
main_menu.add(KeyboardButton("🎬 Видео"), KeyboardButton("🎵 Аудио"))
main_menu.add(KeyboardButton("ℹ️ Инфо"), KeyboardButton("📋 Главное меню"))

admin_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
admin_menu.add(KeyboardButton("🎬 Видео"), KeyboardButton("🎵 Аудио"))
admin_menu.add(KeyboardButton("ℹ️ Инфо"), KeyboardButton("➕ Добавить канал"))
admin_menu.add(KeyboardButton("➖ Удалить канал"), KeyboardButton("📋 Главное меню"))

bot.set_my_commands([
    BotCommand("start", "🚀 Главное меню"),
    BotCommand("video", "🎬 Скачать видео"),
    BotCommand("audio", "🎵 Скачать аудио"),
    BotCommand("info", "ℹ️ Информация о видео"),
])

def is_valid_url(url):
    platforms = {
        'youtube': ['youtube.com/watch', 'youtube.com/shorts', 'youtu.be'],
        'instagram': ['instagram.com/p/', 'instagram.com/reel/', 'instagram.com/tv/', 'instagram.com'],
        'tiktok': ['tiktok.com/@', 'vm.tiktok.com', 'vt.tiktok.com'],
        'rutube': ['rutube.ru/video/', 'rutube.ru/embed/'],
        'vk': ['vk.com/video', 'm.vk.com/video'],
        'likee': ['likee.video', 'likee.in']
    }
    url = url.lower().strip()
    for platform, patterns in platforms.items():
        for pattern in patterns:
            if pattern in url:
                return platform
    return None

def get_video_info(url):
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'N/A'),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'upload_date': info.get('upload_date', 'N/A'),
                'description': info.get('description', 'N/A')[:500] + '...' if len(info.get('description', '')) > 500 else info.get('description', 'N/A'),
                'uploader': info.get('uploader', 'N/A'),
                'channel_url': info.get('channel_url', 'N/A'),
            }
    except:
        return None

def get_user_menu(user_id):
    return admin_menu if user_id == ADMIN_ID else main_menu

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    unsubscribed = check_subscription(user_id, message.chat.id)
    if unsubscribed:
        show_subscription_keyboard(message, unsubscribed)
    else:
        users[user_id] = {'subscribed': True}
        save_users(users)
        send_welcome_message(message)

def send_welcome_message(message):
    bot.reply_to(message,
                 "🎥 **UNIVERSAL VIDEO DOWNLOADER** ✅\n\n"
                 "📱 **Платформы:** YouTube • Instagram • TikTok • Rutube • VK • Likee\n\n"
                 "👇 **Нажми кнопку ниже или отправь ссылку!**",
                 parse_mode='Markdown', reply_markup=get_user_menu(message.from_user.id))

def show_subscription_keyboard(message, unsubscribed):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, channel in enumerate(unsubscribed, 1):
        markup.add(InlineKeyboardButton(f"{i}. {channel['name']}", url=f"https://t.me/{channel['username']}"))
    markup.add(InlineKeyboardButton("✅ Подписаться и продолжить", callback_data="check_sub"))
    
    text = "🔗 **Подпишись на каналы для доступа к боту:**\n\n"
    for i, channel in enumerate(unsubscribed, 1):
        text += f"{i}. {channel['name']}\n"
    text += "\n✅ После подписки нажми кнопку ниже!"
    
    bot.reply_to(message, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🎬 Видео", "📋 Главное меню"])
def video_mode(message):
    check_user_subscription(message)
    bot.reply_to(message, "🎬 **VIDEO MODE** ✅\n📤 Отправь ссылку на видео!", parse_mode='Markdown',
                 reply_markup=get_user_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🎵 Аудио")
def audio_mode(message):
    check_user_subscription(message)
    bot.reply_to(message, "🎵 **AUDIO MODE** ✅\n📤 Отправь ссылку для аудио!", parse_mode='Markdown',
                 reply_markup=get_user_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "ℹ️ Инфо")
def info_mode(message):
    check_user_subscription(message)
    bot.reply_to(message, "ℹ️ **INFO MODE** ✅\n📊 Отправь ссылку для информации!", parse_mode='Markdown',
                 reply_markup=get_user_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text == "➕ Добавить канал")
def add_channel(message):
    bot.reply_to(message, "➕ **Добавление канала**\n\n📤 Отправь ссылку на канал (@username или t.me/username):",
                 parse_mode='Markdown', reply_markup=admin_menu)

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text == "➖ Удалить канал")
def delete_channel_menu(message):
    if not channels:
        bot.reply_to(message, "📭 **Список каналов пуст**", reply_markup=admin_menu)
        return
    markup = InlineKeyboardMarkup(row_width=1)
    for i, channel in enumerate(channels):
        markup.add(InlineKeyboardButton(f"{i + 1}. {channel['name']}", callback_data=f"del_{i}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    
    text = "➖ **Выбери канал для удаления:**\n\n"
    for i, channel in enumerate(channels):
        text += f"{i + 1}. {channel['name']}\n"
    bot.reply_to(message, text, parse_mode='Markdown', reply_markup=markup)

def check_user_subscription(message):
    user_id = message.from_user.id
    unsubscribed = check_subscription(user_id, message.chat.id)
    if unsubscribed:
        show_subscription_keyboard(message, unsubscribed)
        return False
    return True

@bot.message_handler(content_types=['text'])
def handle_url(message):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID and message.reply_to_message:
        if "Добавление канала" in message.reply_to_message.text:
            add_channel_handler(message)
            return
    
    if not check_user_subscription(message):
        return
    
    url = message.text.strip()
    platform = is_valid_url(url)
    
    if not platform:
        bot.reply_to(message,
                     "❌ **Неподдерживаемая платформа**\n\n"
                     "✅ **Работает с:**\n• youtube.com\n• instagram.com/p/\n• instagram.com/reel/\n• tiktok.com\n• rutube.ru\n• vk.com/video\n• likee.video\n\n👇 **Используй кнопки!**",
                     parse_mode='Markdown', reply_markup=get_user_menu(user_id))
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 ВИДЕО", callback_data=f"video_{url}"),
        InlineKeyboardButton("🎵 АУДИО", callback_data=f"audio_{url}"),
        InlineKeyboardButton("ℹ️ ИНФО", callback_data=f"info_{url}")
    )
    bot.reply_to(message, f"✅ **{platform.upper()} найден!**\n🎯 Выбери действие:",
                 reply_markup=markup, parse_mode='Markdown')

def add_channel_handler(message):
    channel_link = message.text.strip()
    if channel_link.startswith('@'):
        username = channel_link[1:]
    elif channel_link.startswith('t.me/'):
        username = channel_link.split('t.me/')[1].split('/')[0]
    elif channel_link.startswith('https://t.me/'):
        username = channel_link.split('t.me/')[1].split('/')[0]
    else:
        bot.reply_to(message, "❌ Неверный формат! Используй: @username или t.me/username", reply_markup=admin_menu)
        return
    
    try:
        chat = bot.get_chat(f"@{username}")
        channel_info = {
            'chat_id': chat.id,
            'username': username,
            'name': chat.title or chat.username or username,
            'id': len(channels)
        }
        channels.append(channel_info)
        save_channels(channels)
        bot.reply_to(message, f"✅ **Канал добавлен!**\n\n📢 {channel_info['name']}\n🆔 @{username}",
                     parse_mode='Markdown', reply_markup=admin_menu)
    except Exception as e:
        bot.reply_to(message, f"❌ **Ошибка:** {str(e)}\nПроверь права бота и ссылку!", reply_markup=admin_menu)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)
    
    if data == "check_sub":
        unsubscribed = check_subscription(user_id, call.message.chat.id)
        if not unsubscribed:
            users[user_id] = {'subscribed': True}
            save_users(users)
            bot.edit_message_text("✅ **Подписка подтверждена!**\n\n🚀 Теперь можешь использовать бота!",
                                  call.message.chat.id, call.message.id,
                                  reply_markup=get_user_menu(user_id), parse_mode='Markdown')
            return
        bot.answer_callback_query(call.id, "❌ Подпишись на все каналы!")
        return
    
    if data == "admin_back":
        bot.edit_message_text("🔙 **Админ панель**\n\nВыбери действие:",
                              call.message.chat.id, call.message.id,
                              reply_markup=admin_menu, parse_mode='Markdown')
        return
    
    if data.startswith("del_") and user_id == ADMIN_ID:
        index = int(data.split('_')[1])
        if 0 <= index < len(channels):
            removed = channels.pop(index)
            save_channels(channels)
            bot.edit_message_text(f"✅ **Канал удален!**\n\n🗑️ {removed['name']}\n🆔 @{removed['username']}",
                                  call.message.chat.id, call.message.id,
                                  reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back")))
        return
    
    unsubscribed = check_subscription(user_id, call.message.chat.id)
    if unsubscribed:
        bot.edit_message_text("🔗 **Подпишись на каналы!**", call.message.chat.id, call.message.id)
        return
    
    bot.edit_message_text("⏳ Обрабатываю...", call.message.chat.id, call.message.id)
    
    try:
        action, url = data.split('_', 1)
        if action == 'video':
            download_video(url, call.message.chat.id, call.message.id)
        elif action == 'audio':
            download_audio(url, call.message.chat.id, call.message.id)
        elif action == 'info':
            show_info(url, call.message.chat.id, call.message.id)
    except:
        bot.edit_message_text("❌ **Ошибка**\n👇 Вернись в меню", call.message.chat.id, call.message.id,
                              reply_markup=get_user_menu(user_id))

def show_info(url, chat_id, message_id):
    info = get_video_info(url)
    if not info:
        bot.edit_message_text("❌ Не удалось получить информацию", chat_id, message_id,
                              reply_markup=main_menu)
        return
    
    duration = f"{info['duration'] // 60}:{info['duration'] % 60:02d}" if info['duration'] else "N/A"
    views = f"{info['view_count']:,}" if info['view_count'] else "N/A"
    likes = f"{info['like_count']:,}" if info['like_count'] else "N/A"
    
    info_text = f"""📊 **ИНФО ВИДЕО**

🎬 **Название:** {info['title']}
⏱ **Длительность:** {duration}
👀 **Просмотры:** {views}
❤️ **Лайки:** {likes}
📅 **Дата:** {info['upload_date']}
👤 **Автор:** {info['uploader']}

📝 **Описание:**
{info['description']}"""
    
    markup = InlineKeyboardMarkup()
    if info['channel_url']:
        markup.add(InlineKeyboardButton("👤 Канал", url=info['channel_url']))
    markup.add(InlineKeyboardButton("🏠 Меню", callback_data="back_menu"))
    
    bot.edit_message_text(info_text, chat_id, message_id, parse_mode='Markdown',
                          reply_markup=markup, disable_web_page_preview=True)

def download_video(url, chat_id, message_id):
    ydl_opts = {
        'format': 'best[height<=720][filesize<=50M]/best[filesize<=50M]/best',
        'outtmpl': f'{DATA_DIR}/downloads/video/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            
            files = [f for f in os.listdir(f'{DATA_DIR}/downloads/video') if os.path.getsize(f'{DATA_DIR}/downloads/video/{f}') > 10000]
            if files:
                latest_file = max(files, key=lambda f: os.path.getctime(f'{DATA_DIR}/downloads/video/{f}'))
                file_path = f'{DATA_DIR}/downloads/video/{latest_file}'
                
                if os.path.getsize(file_path) < 50 * 1024 * 1024:
                    with open(file_path, 'rb') as video:
                        bot.send_video(chat_id, video, caption=f"🎬 {title[:90]} ✅",
                                       reply_markup=get_user_menu(chat_id))
                    os.remove(file_path)
                    bot.edit_message_text("✅ **Видео отправлено!** 👇 Меню ниже", chat_id, message_id,
                                          reply_markup=get_user_menu(chat_id))
                else:
                    os.remove(file_path)
                    bot.edit_message_text("❌ **Файл >50MB**\n👇 Вернись в меню", chat_id, message_id,
                                          reply_markup=get_user_menu(chat_id))
            else:
                bot.edit_message_text("❌ Не удалось скачать\n👇 Вернись в меню", chat_id, message_id,
                                      reply_markup=get_user_menu(chat_id))
    except Exception as e:
        bot.edit_message_text(f"❌ **Ошибка:** {str(e)}\n👇 Вернись в меню", chat_id, message_id,
                              reply_markup=get_user_menu(chat_id))

def download_audio(url, chat_id, message_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DATA_DIR}/downloads/audio/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
            
            mp3_files = [f for f in os.listdir(f'{DATA_DIR}/downloads/audio') if f.endswith('.mp3')]
            if mp3_files:
                latest_mp3 = max(mp3_files, key=lambda f: os.path.getctime(f'{DATA_DIR}/downloads/audio/{f}'))
                file_path = f'{DATA_DIR}/downloads/audio/{latest_mp3}'
                
                with open(file_path, 'rb') as audio:
                    bot.send_audio(chat_id, audio, title=title[:90],
                                   performer=info.get('uploader', 'Unknown'),
                                   reply_markup=get_user_menu(chat_id))
                os.remove(file_path)
                bot.edit_message_text("✅ **Аудио отправлено!** 👇 Меню ниже", chat_id, message_id,
                                      reply_markup=get_user_menu(chat_id))
            else:
                bot.edit_message_text("❌ Не удалось извлечь аудио\n👇 Вернись в меню", chat_id, message_id,
                                      reply_markup=get_user_menu(chat_id))
    except Exception as e:
        bot.edit_message_text(f"❌ **Ошибка:** {str(e)}\n👇 Вернись в меню", chat_id, message_id,
                              reply_markup=get_user_menu(chat_id))

def run_bot():
    while True:
        try:
            logger.info("🚀 Video Downloader Bot запущен на Render!")
            print("🚀 Бот запущен!")
            bot.polling(none_stop=True, interval=1, timeout=10)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            time.sleep(10)

if __name__ == '__main__':
    run_bot()
