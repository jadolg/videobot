import logging
import os

import humanize
import requests
import telegram
import youtube_dl
from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

VIDEO, OPTION_SELECT = range(2)


def download_options(video_url):
    ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s.%(ext)s'})

    with ydl:
        result = ydl.extract_info(
            video_url,
            download=False
        )

    if 'entries' in result:
        video = result['entries'][0]
    else:
        video = result

    video_options = []

    for video_format in video['formats']:
        video_options.append({
            'ext': video_format['ext'],
            'size': video_format['filesize'] if video_format['filesize'] else 0,
            'format': video_format['format'],
            'url': video_format['url']
        })

    return video_options


def start(update: Update, _: CallbackContext) -> int:
    update.message.reply_text("Hey there. I'll download videos for you from YouTube. Type here the whole URL so I can "
                              "give you options.", reply_markup=ReplyKeyboardRemove())
    return VIDEO


def video(update: Update, context: CallbackContext) -> int:
    video_url = update.message.text
    if not video_url.startswith("https://www.youtube.com/watch?v="):
        update.message.reply_text(f"that is not a valid youtube video")
        return ConversationHandler.END

    options = download_options(video_url)
    context.user_data['video_url'] = video_url

    reply_keyboard = []
    indexed_options = {}
    for option in options:
        indexed_options[f"{option['format']} - {humanize.naturalsize(option['size'])}"] = option
        reply_keyboard.append([f"{option['format']} - {humanize.naturalsize(option['size'])}"])
    context.user_data['video_options'] = indexed_options
    update.message.reply_text(
        'Please select an option?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )

    return OPTION_SELECT


def option(update: Update, context: CallbackContext) -> int:
    if update.message.text in context.user_data['video_options']:
        try:
            url = context.user_data['video_options'][update.message.text]['url']
            logger.info(f"Downloading {url}")
            response = requests.get(url)
            update.message.reply_video(video=response.content)
            response.close()
        except Exception as a:
            print(a)
            update.message.reply_text(f"something went wrong :'(")
    else:
        update.message.reply_text(f"that is not a valid youtube video")

    return ConversationHandler.END


def cancel(bot, update, user_data):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('bye', reply_markup=telegram.ReplyKeyboardMarkup([['/start']]))
    user_data.clear()

    return ConversationHandler.END


TOKEN = os.environ.get('TELEGRAM_TOKEN')
updater = Updater(TOKEN)
dp = updater.dispatcher

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],

    states={
        VIDEO: [MessageHandler(Filters.text, video, pass_user_data=True)],
        OPTION_SELECT: [MessageHandler(Filters.text, option, pass_user_data=True)],
    },

    fallbacks=[MessageHandler(Filters.text, cancel, pass_user_data=True),
               CommandHandler('cancelar', cancel, pass_user_data=True)]
)

dp.add_handler(conv_handler)
updater.start_polling()
updater.idle()
