import logging
import os

import humanize
import youtube_dl
from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup, ChatAction
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
        if video_format['acodec'] != 'none':
            video_options.append({
                'ext': video_format['ext'],
                'size': video_format['filesize'] if video_format['filesize'] else 0,
                'format': video_format['format'],
                'format_id': video_format['format_id'],
                'url': video_format['url']
            })

    return video_options, video['title']


def start(update: Update, _: CallbackContext) -> int:
    update.message.reply_text("Hey there. I'll download videos for you from YouTube. Type here the whole URL so I can "
                              "give you options.", reply_markup=ReplyKeyboardRemove())
    return VIDEO


def video(update: Update, context: CallbackContext) -> int:
    context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
    video_url = update.message.text
    logger.info("User %s trying to download %s", update.message.from_user, video_url)

    try:
        options, title = download_options(video_url)
        context.user_data['video_url'] = video_url

        context.user_data['video_title'] = "".join(x for x in title if x.isalnum())

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
    except Exception as e:
        logger.error(e)
        update.message.reply_text(f"that is not a valid youtube video")
        return VIDEO


def option(update: Update, context: CallbackContext) -> int:
    if update.message.text in context.user_data['video_options']:
        try:
            if "audio only" in update.message.text:
                context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.UPLOAD_AUDIO)
                ext = "mp3"
                output_file = f'{context.user_data["video_title"]}.{ext}'
                ydl_opts = {
                    'format': context.user_data['video_options'][update.message.text]['format_id'],
                    'outtmpl': output_file,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([context.user_data['video_url']])
                update.message.reply_audio(audio=open(output_file, 'rb'))
            else:
                context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.UPLOAD_VIDEO)
                ext = context.user_data['video_options'][update.message.text]['ext']

                output_file = f'{context.user_data["video_title"]}.{ext}'
                ydl_opts = {
                    'format': context.user_data['video_options'][update.message.text]['format_id'],
                    'outtmpl': output_file,
                }

                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([context.user_data['video_url']])

                update.message.reply_video(video=open(output_file, 'rb'))

        except Exception as a:
            print(a)
            update.message.reply_text(f"something went wrong :'(")
            return VIDEO
    else:
        update.message.reply_text(f"that is not a valid video option")
        return OPTION_SELECT

    update.message.reply_text(f"I'm ready to download another video for you")
    return VIDEO


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    reply_keyboard = [["/start"]]
    update.message.reply_text(
        'Bye! I hope we can talk again some day. Send /start to begin again.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
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
               CommandHandler('cancel', cancel, pass_user_data=True)]
)

dp.add_handler(conv_handler)
updater.start_polling()
updater.idle()
