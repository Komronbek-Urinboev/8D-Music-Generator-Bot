import os
import math
import random
import threading
import queue
import uuid
import subprocess
import telebot
from telebot import apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pydub import AudioSegment
from pydub.effects import normalize

# ==========================================
# ⚙️ ОСНОВНЫЕ НАСТРОЙКИ БОТА
# ==========================================
TOKEN = 'TOKEN'  # Вставь свой токен!
ADMIN_ID = 1234567890
CHANNEL_ID = -0987654321
PHOTO_FILE = "my_i.jpg"  # Вертикальное фото (9:16)
VIDEO_CAPTION = "🔥 @musicgen_8d #reels"

# Настройки эквалайзера видео
EQ_BOTTOM_OFFSET = 30
EQ_HEIGHT = 300
EQ_COLOR = "0xE6F8FF"
EQ_OPACITY = "0.6"

apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 300

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 🗄 БАЗА ДАННЫХ И ОЧЕРЕДИ
# ==========================================
audio_queue = queue.Queue()
video_queue = queue.Queue()
user_data = {}
video_cache = {}  # Для хранения file_id сгенерированных треков
stats = {"audio_processed": 0, "video_processed": 0}

# ==========================================
# 🌍 МУЛЬТИЯЗЫЧНЫЕ ТЕКСТЫ (ПОЛНАЯ ВЕРСИЯ)
# ==========================================
TEXTS = {
    'ru': {
        'lang_cmd': "🌍 Выберите язык / Choose language / Tilni tanlang:",
        'lang_set': "✅ Язык установлен на Русский.",
        'welcome': "🎧 <b>True 8D & Reels Бот</b>\n\nОтправь мне аудио (до 20 МБ), чтобы сделать 8D трек. После этого ты сможешь сгенерировать залипательное Reels видео для TikTok/Insta/TG!",
        'too_big': "❌ Файл слишком большой. Лимит — 20 МБ.",
        'choose_speed': "⚙️ Выбери скорость вращения:",
        'speed_slow': "🐢 Медленно",
        'speed_normal': "🚶‍♂️ Стандарт",
        'speed_fast': "🌪 Ураган",
        'queued_audio': "✅ Трек в очереди (Позиция: <b>{pos}</b>). Ожидание ~{time} сек.",
        'processing_audio': "🎧 Синтезирую 3D-пространство (HRTF)...",
        'sending_audio': "📤 Отправляю 8D трек...",
        'ask_video': "🎵 Трек готов! Хочешь сделать из него Reels видео с эквалайзером?",
        'make_vid_btn': "🎬 Сделать Reels (9:16)",
        'queued_video': "✅ Видео в очереди (Позиция: <b>{pos}</b>).",
        'processing_video': "🎬 Рендерю Reels... Это займет пару минут.",
        'sending_video': "📤 Видео готово! Загружаю...",
        'error': "❌ Ошибка: {err}"
    },
    'en': {
        'lang_cmd': "🌍 Choose your language:",
        'lang_set': "✅ Language set to English.",
        'welcome': "🎧 <b>True 8D & Reels Bot</b>\n\nSend me an audio (up to 20 MB) to create an 8D track. After that, you can generate an amazing Reels video for TikTok/Insta/TG!",
        'too_big': "❌ File too large. Limit is 20 MB.",
        'choose_speed': "⚙️ Choose rotation speed:",
        'speed_slow': "🐢 Slow",
        'speed_normal': "🚶‍♂️ Normal",
        'speed_fast': "🌪 Hurricane",
        'queued_audio': "✅ Track queued (Position: <b>{pos}</b>). Wait ~{time} sec.",
        'processing_audio': "🎧 Synthesizing 3D space (HRTF)...",
        'sending_audio': "📤 Sending 8D track...",
        'ask_video': "🎵 Track is ready! Want to make an equalizer Reels video from it?",
        'make_vid_btn': "🎬 Make Reels (9:16)",
        'queued_video': "✅ Video queued (Position: <b>{pos}</b>).",
        'processing_video': "🎬 Rendering Reels... This will take a few minutes.",
        'sending_video': "📤 Video ready! Uploading...",
        'error': "❌ Error: {err}"
    },
    'uz': {
        'lang_cmd': "🌍 Tilni tanlang:",
        'lang_set': "✅ Til O'zbekchaga o'zgartirildi.",
        'welcome': "🎧 <b>True 8D & Reels Bot</b>\n\nMenga 8D trek yaratish uchun audio (20 MB gacha) yuboring. Shundan so'ng siz TikTok/Insta/TG uchun ajoyib Reels videosini yaratishingiz mumkin!",
        'too_big': "❌ Fayl juda katta. Limit — 20 MB.",
        'choose_speed': "⚙️ Aylanish tezligini tanlang:",
        'speed_slow': "🐢 Sekin",
        'speed_normal': "🚶‍♂️ Standart",
        'speed_fast': "🌪 Bo'ron",
        'queued_audio': "✅ Trek navbatda (O'rningiz: <b>{pos}</b>). Kutish ~{time} soniya.",
        'processing_audio': "🎧 3D makon yaratilmoqda (HRTF)...",
        'sending_audio': "📤 8D trek yuborilmoqda...",
        'ask_video': "🎵 Trek tayyor! Undan ekvalayzerli Reels video yaratishni xohlaysizmi?",
        'make_vid_btn': "🎬 Reels yaratish (9:16)",
        'queued_video': "✅ Video navbatda (O'rningiz: <b>{pos}</b>).",
        'processing_video': "🎬 Reels yaratilmoqda... Bu bir necha daqiqa vaqt oladi.",
        'sending_video': "📤 Video tayyor! Yuklanmoqda...",
        'error': "❌ Xatolik: {err}"
    }
}


def get_text(user_id, key, **kwargs):
    lang = user_data.get(user_id, {}).get('lang', 'ru')
    text = TEXTS.get(lang, TEXTS['ru']).get(key, TEXTS['ru'].get(key, "Текст не найден"))
    return text.format(**kwargs) if kwargs else text


# КЛАВИАТУРА ВЫБОРА ЯЗЫКА
def lang_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇷🇺 Русс", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 Eng", callback_data="lang_en"),
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
    )
    return markup


# ==========================================
# 🎵 АУДИО ДВИЖОК: TRUE 8D / 16D
# ==========================================
def match_mono_lengths(mono1, mono2):
    len1, len2 = len(mono1._data), len(mono2._data)
    if len1 == len2: return mono1, mono2
    min_bytes = min(len1, len2)
    sw = mono1.sample_width
    min_bytes = (min_bytes // sw) * sw
    return (mono1._spawn(mono1._data[:min_bytes]) if len1 > min_bytes else mono1,
            mono2._spawn(mono2._data[:min_bytes]) if len2 > min_bytes else mono2)


def add_room_ambience(audio_segment):
    muffled = audio_segment.low_pass_filter(2000) - 12
    left, right = muffled.split_to_mono()
    delay = AudioSegment.silent(duration=20, frame_rate=right.frame_rate)
    right_delayed = delay + right
    left, right_delayed = match_mono_lengths(left, right_delayed)
    return AudioSegment.from_mono_audiosegments(left, right_delayed)


def process_true_8d(input_path: str, output_path: str, speed_mode: str, chunk_ms: int = 120):
    audio = AudioSegment.from_file(input_path)
    if audio.channels == 1:
        audio = AudioSegment.from_mono_audiosegments(audio, audio)
    if audio.frame_rate < 44100:
        audio = audio.set_frame_rate(44100)

    max_freq = min(18000, int(audio.frame_rate / 2) - 1000)
    period_sec = {'slow': 16.0, 'fast': 4.0}.get(speed_mode, 8.0)

    chunks = []
    total_length = len(audio)
    current_angle = 0.0

    for i in range(0, total_length, chunk_ms):
        chunk = audio[i: i + chunk_ms]
        t = i / 1000.0

        # ЖИВАЯ ДИНАМИКА
        speed_multiplier = 1.0 + math.sin(t * 0.4) * 0.3
        delta_angle = ((chunk_ms / 1000.0) / period_sec) * 2 * math.pi * speed_multiplier
        current_angle += delta_angle

        x_pan = math.sin(current_angle)
        y_depth = math.cos(current_angle)

        cutoff = max_freq
        vol_drop = 0

        if y_depth < 0:
            cutoff = max_freq - (abs(y_depth) * 7000)
            vol_drop = abs(y_depth) * 4.0

        cutoff = max(1500, int(cutoff))

        if cutoff < (max_freq - 1500):
            chunk = chunk.low_pass_filter(cutoff)

        if vol_drop > 0:
            chunk = chunk - vol_drop

        chunk = chunk.pan(x_pan)
        chunks.append(chunk)

    main_8d_track = sum(chunks)
    room_layer = add_room_ambience(audio) - 3
    final_audio = main_8d_track.overlay(room_layer)
    final_audio = normalize(final_audio)

    final_audio.export(output_path, format="mp3", bitrate="320k", parameters=["-ar", "44100"])


# ==========================================
# 🎬 ВИДЕО ДВИЖОК: REELS ГЕНЕРАТОР
# ==========================================
def create_reels_freqs_video(image_path, audio_path, output_path):
    command = [
        'ffmpeg', '-loop', '1', '-framerate', '30',
        '-i', image_path, '-i', audio_path,
        '-filter_complex',
        f'[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];'
        f'[1:a]showfreqs=s=1080x{EQ_HEIGHT}:mode=bar:ascale=log:fscale=log:colors={EQ_COLOR}[eq];'
        '[eq]colorkey=0x000000:0.1:0.1[eq_no_bg];'
        f'[eq_no_bg]format=rgba,colorchannelmixer=aa={EQ_OPACITY}[eq_transparent];'
        f'[bg][eq_transparent]overlay=0:H-h-{EQ_BOTTOM_OFFSET}[outv]',
        '-map', '[outv]', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '320k', '-shortest', '-y', output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# ==========================================
# 🛠 ВОРКЕРЫ (ФОНОВЫЕ ПОТОКИ)
# ==========================================
def audio_worker():
    while True:
        task = audio_queue.get()
        message, speed_mode = task['message'], task['speed']
        user_id = message.chat.id
        task_id = str(uuid.uuid4())

        in_name = f"in_{task_id}.mp3"
        out_name = f"8d_{task_id}.mp3"

        try:
            msg_status = bot.send_message(user_id, get_text(user_id, 'processing_audio'))

            file_info = bot.get_file(message.audio.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(in_name, 'wb') as f:
                f.write(downloaded)

            process_true_8d(in_name, out_name, speed_mode)
            bot.edit_message_text(get_text(user_id, 'sending_audio'), chat_id=user_id, message_id=msg_status.message_id)

            title = message.audio.title or "True 8D"
            performer = message.audio.performer or "8D Bot"

            with open(out_name, 'rb') as audio_file:
                sent_audio = bot.send_audio(user_id, audio_file, title=f"8D | {title}", performer=performer)

            bot.delete_message(user_id, msg_status.message_id)
            stats["audio_processed"] += 1

            # Сохраняем ID трека для генерации видео
            cache_id = task_id[:8]
            video_cache[cache_id] = {
                'file_id': sent_audio.audio.file_id,
                'title': title,
                'performer': performer
            }

            # Предлагаем сделать видео
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(get_text(user_id, 'make_vid_btn'), callback_data=f"vid_{cache_id}"))
            bot.send_message(user_id, get_text(user_id, 'ask_video'), reply_markup=markup)

            # Отправка аудио в канал
            try:
                bot.send_audio(CHANNEL_ID, sent_audio.audio.file_id, caption="🔥 @musicgen_8d")
            except Exception as e:
                print("Ошибка отправки аудио в канал:", e)

        except Exception as e:
            bot.send_message(user_id, get_text(user_id, 'error', err=str(e)))
        finally:
            if os.path.exists(in_name): os.remove(in_name)
            if os.path.exists(out_name): os.remove(out_name)
            audio_queue.task_done()


def video_worker():
    while True:
        task = video_queue.get()
        user_id = task['user_id']
        audio_data = task['audio_data']
        task_id = str(uuid.uuid4())

        in_audio = f"vid_in_{task_id}.mp3"
        out_video = f"vid_out_{task_id}.mp4"

        try:
            msg_status = bot.send_message(user_id, get_text(user_id, 'processing_video'))

            file_info = bot.get_file(audio_data['file_id'])
            downloaded = bot.download_file(file_info.file_path)
            with open(in_audio, 'wb') as f:
                f.write(downloaded)

            create_reels_freqs_video(PHOTO_FILE, in_audio, out_video)
            bot.edit_message_text(get_text(user_id, 'sending_video'), chat_id=user_id, message_id=msg_status.message_id)

            track_name = f"{audio_data['performer']} - {audio_data['title']}"
            caption = f"{VIDEO_CAPTION}\n🎧 Трек: {track_name}"

            with open(out_video, 'rb') as video_file:
                sent_vid = bot.send_video(user_id, video_file, caption=caption, timeout=300)

            bot.delete_message(user_id, msg_status.message_id)
            stats["video_processed"] += 1

            # Отправка видео в канал
            try:
                bot.send_video(CHANNEL_ID, sent_vid.video.file_id, caption=caption, timeout=300)
            except Exception as e:
                print("Ошибка видео в канал:", e)

        except Exception as e:
            bot.send_message(user_id, get_text(user_id, 'error', err=str(e)))
        finally:
            if os.path.exists(in_audio): os.remove(in_audio)
            if os.path.exists(out_video): os.remove(out_video)
            video_queue.task_done()


threading.Thread(target=audio_worker, daemon=True).start()
threading.Thread(target=video_worker, daemon=True).start()


# ==========================================
# 📱 ОБРАБОТЧИКИ КОМАНД И КНОПОК
# ==========================================
@bot.message_handler(commands=['lang'])
def cmd_lang(message):
    bot.send_message(message.chat.id, TEXTS['ru']['lang_cmd'], reply_markup=lang_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    try:
        # ОБЯЗАТЕЛЬНО: отвечает Telegram, что кнопка нажата, снимает "часики" загрузки
        bot.answer_callback_query(call.id)

        lang_code = call.data.split('_')[1]
        user_id = call.message.chat.id
        if user_id not in user_data: user_data[user_id] = {}
        user_data[user_id]['lang'] = lang_code

        # Используем строгие именованные параметры
        bot.edit_message_text(get_text(user_id, 'lang_set'), chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, get_text(user_id, 'welcome'), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка в выборе языка: {e}")


@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.chat.id
    if user_id not in user_data:
        bot.send_message(user_id, TEXTS['ru']['lang_cmd'], reply_markup=lang_keyboard())
    else:
        bot.send_message(user_id, get_text(user_id, 'welcome'), parse_mode="HTML")


@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    if message.from_user.id != ADMIN_ID: return
    text = f"🛠 <b>Статистика</b>\nЮзеров: {len(user_data)}\nТреков: {stats['audio_processed']}\nВидео: {stats['video_processed']}\nОчередь аудио: {audio_queue.qsize()}\nОчередь видео: {video_queue.qsize()}"
    bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    user_id = message.chat.id
    if user_id not in user_data: user_data[user_id] = {'lang': 'ru'}

    if message.audio.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, get_text(user_id, 'too_big'))
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(get_text(user_id, 'speed_slow'), callback_data="speed_slow"),
        InlineKeyboardButton(get_text(user_id, 'speed_normal'), callback_data="speed_normal"),
        InlineKeyboardButton(get_text(user_id, 'speed_fast'), callback_data="speed_fast")
    )
    bot.reply_to(message, get_text(user_id, 'choose_speed'), reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('speed_'))
def queue_audio_task(call):
    try:
        bot.answer_callback_query(call.id)  # Обязательно снимаем часики с кнопки!
        speed_mode = call.data.split('_')[1]
        user_id = call.message.chat.id

        original = call.message.reply_to_message
        if not original or not original.audio:
            bot.send_message(user_id, "❌ Не найден исходный файл.")
            return

        audio_queue.put({'message': original, 'speed': speed_mode})
        wait_time = audio_queue.qsize() * 20

        # Обновляем текст, заодно убирая кнопки
        bot.edit_message_text(get_text(user_id, 'queued_audio', pos=audio_queue.qsize(), time=wait_time),
                              chat_id=user_id, message_id=call.message.message_id, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка в выборе скорости: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('vid_'))
def queue_video_task(call):
    try:
        cache_id = call.data.split('_')[1]
        user_id = call.message.chat.id

        if cache_id not in video_cache:
            bot.answer_callback_query(call.id, "❌ Трек устарел или не найден.", show_alert=True)
            bot.edit_message_text("❌ Этот трек больше не доступен для генерации видео.", chat_id=user_id,
                                  message_id=call.message.message_id)
            return

        bot.answer_callback_query(call.id)  # Снимаем часики загрузки
        video_queue.put({'user_id': user_id, 'audio_data': video_cache[cache_id]})

        bot.edit_message_text(get_text(user_id, 'queued_video', pos=video_queue.qsize()),
                              chat_id=user_id, message_id=call.message.message_id, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка в генерации видео: {e}")


if __name__ == "__main__":
    print("🤖 Бот запущен! Ошибки кнопок устранены.")
    # none_stop гарантирует, что бот не упадет при сбоях сети
    bot.polling(none_stop=True, long_polling_timeout=120)
