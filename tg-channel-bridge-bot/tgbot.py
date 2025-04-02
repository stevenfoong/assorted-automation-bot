#!/usr/bin/env python3

import logging
import os
import sys

import sqlite3

#import mimetypes
#import magic
import filetype

def check_file_exists(file_path):
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        sys.exit(1)  # Exit the program with a non-zero status

dbfile = 'tgbot.db'
check_file_exists(dbfile)

try:

    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute('select * from groups_map')
    rows = cur.fetchall()
    conn.close()

    groups_map = {}

    for row in rows:
        groups_map[row[0]] = row[1]

    print("Groups Mapping:")
    print(groups_map)

except Exception as e:
    logging.error(e)
    sys.exit(1)

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, Updater, CallbackQueryHandler, CallbackContext

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

tg_bot_token = os.environ.get("TG_BOT_TOKEN")
if not tg_bot_token:
    print("missing config TG_BOT_TOKEN")
    sys.exit(1)

admin_group_id = os.environ.get("ADMIN_GROUP_ID")
if not admin_group_id:
    print("missing config ADMIN_GROUP_ID")
    sys.exit(1)

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("***")
    print(update)
    print("***")

async def command_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("*** Command ***")
    print(update)
    print("***")

async def add_conversation(conversations):
    sql = '''INSERT INTO conversations_map(group1_id,group1_msg_id,group2_id,group2_msg_id)
             VALUES(?,?,?,?) '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute(sql, conversations)
    conn.commit()
    conn.close()
    return cur.lastrowid

def retrieve_conversation(conversations):
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    sql = '''SELECT group1_msg_id FROM conversations_map where group2_id=? and group2_msg_id=? and group1_id=?'''
    cur.execute(sql, conversations)
    data=cur.fetchone()

    if data is None:
        sql = '''SELECT group2_msg_id FROM conversations_map where group1_id=? and group1_msg_id=? and group2_id=?'''
        cur.execute(sql, conversations)
        data=cur.fetchone()

    conn.close()
    if data is None:
        return "Conversation not found"
    else: 
        return data[0]

def check_group_mapping(channels):
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    sql1 = '''SELECT * FROM groups_map where group1=? and group2=?'''
    cur.execute(sql1, channels)
    data1=cur.fetchone()

    #print(channels)
    #print(channels[0])

    if data1 is None:
        sql1 = '''SELECT * FROM groups_map where group2=? and group1=?'''
        cur.execute(sql1, channels)
        data1=cur.fetchone()

    sql2 = '''SELECT * FROM groups_map where group1=?'''
    sql3 = '''SELECT * FROM groups_map where group2=?'''
    cur.execute(sql2, [channels[0]])
    data2=cur.fetchone()

    if data2 is None:
        cur.execute(sql3, [channels[0]])
        data2=cur.fetchone()

    cur.execute(sql2, [channels[1]])
    data3=cur.fetchone()

    if data3 is None:
        cur.execute(sql3, [channels[1]])
        data3=cur.fetchone()

    conn.close()
    if data1 is not None:
        return 1
    if data2 is not None:
        return 2
    if data3 is not None:
        return 3
    if data1 is None and data2 is None and data3 is None:
        return 0
    else:
        return

async def add_group_mapping(channels):

    try:
        sql = '''INSERT INTO groups_map(group1,group2) VALUES(?,?) '''
        conn = sqlite3.connect(dbfile)
        cur = conn.cursor()
        cur.execute(sql, channels)
        conn.commit()
        cur.execute('select * from groups_map')
        rows = cur.fetchall()
        conn.close()

        groups_map.clear()

        for row in rows:
            groups_map[row[0]] = row[1]

        print("Groups Mapping:")
        print(groups_map)

        return 1 

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 0

async def del_group_mapping(channels):

    try:
        print("#delete row#")
        sql='''DELETE FROM groups_map WHERE ((group1 = ? AND group2 = ?) OR (group1 = ? AND group2 = ?)) '''

        #sql = '''INSERT INTO groups_map(group1,group2) VALUES(?,?) '''
        conn = sqlite3.connect(dbfile)
        cur = conn.cursor()
        cur.execute(sql, channels)
        conn.commit()

        cur.execute('select * from groups_map')
        rows = cur.fetchall()
        conn.close()

        groups_map.clear()

        for row in rows:
            groups_map[row[0]] = row[1]

        print("Groups Mapping:")
        print(groups_map)

        return 1

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 0


async def retrieve_channel_id(chat_id):

    dest_channel = []

    if chat_id in groups_map:
        #print("Channel ID found in Key")
        dest_channel.append(groups_map[chat_id])
        dest_channel.append("1")
        return dest_channel

    elif chat_id in groups_map.values():
        #print("Channel ID found in Value")
        dest_channel.append(list(groups_map.keys())[list(groups_map.values()).index(chat_id)])
        dest_channel.append("2")
        return dest_channel

    else:
        print(f"Channel ID {update.message.chat.id} not found")
        return

def format_sender(user_first_name, user_last_name):
    
    #sender = user_first_name + " " + user_last_name
    sender = user_last_name
    return sender


async def forward_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    dest = await retrieve_channel_id(update.message.chat.id)
    #print(dest)
    print("text received")
    print(update)
    print("***")

    dest_channel = dest[0]

    sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

    if dest[1] == "1":
       message = update.message.text

    elif dest[1] == "2":
       message = f"""
        *{sender}* \U0001F5E3 \n
        {update.message.text}
        """
    else:
        return

    try:
        forward_msg_result = await context.bot.send_message(chat_id=dest_channel, text=message, parse_mode=ParseMode.MARKDOWN)
        #print("***")
        #print("Forward message result")
        #print(forward_msg_result)
        #print("***")
        await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])
    
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")

async def reply_forward_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.text

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.text}
            """
        else:
            return

        dest_reply_to_message_id=retrieve_conversation([update.message.chat.id,update.message.reply_to_message.message_id,dest_channel])

        #print(dest_reply_to_message_id)

        if dest_reply_to_message_id=="Conversation not found":

            forward_msg_result = await context.bot.send_message(reply_to_message_id=update.message.reply_to_message.message_id,chat_id=update.message.reply_to_message.chat.id,text=message)
        
        else:
            
            forward_msg_result = await context.bot.send_message(reply_to_message_id=dest_reply_to_message_id,chat_id=dest_channel,text=message)
        
        await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])
    
    except Exception as e:
        logger.error(f"Error replying message: {e}")

async def forward_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:

        file = await context.bot.get_file(update.message.photo[-1].file_id)
        await file.download_to_drive(update.message.photo[-1].file_id)

        kind = filetype.guess(update.message.photo[-1].file_id)

        file_extension = kind.extension
        file_name = update.message.photo[-1].file_id + "." + file_extension
        os.rename(update.message.photo[-1].file_id, file_name)


        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.caption

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.caption}
            """
        else:
            return

        with open(file_name, "rb") as fp:
            forward_msg_result = await context.bot.send_photo(chat_id=dest_channel, photo=fp , caption=message, parse_mode=ParseMode.MARKDOWN)
            await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])
        os.remove(file_name)


    except Exception as e:
        logger.error(f"Error replying message: {e}")

async def reply_forward_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:

        file = await context.bot.get_file(update.message.photo[-1].file_id)
        await file.download_to_drive(update.message.photo[-1].file_id)
        kind = filetype.guess(update.message.photo[-1].file_id)
        file_extension = kind.extension
        file_name = update.message.photo[-1].file_id + "." + file_extension
        os.rename(update.message.photo[-1].file_id, file_name)

        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.caption

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.caption}
            """
        else:
            return

        dest_reply_to_message_id = retrieve_conversation([update.message.chat.id,update.message.reply_to_message.message_id,dest_channel])

        with open(file_name, "rb") as fp:

            if dest_reply_to_message_id=="Conversation not found":

                forward_msg_result = await context.bot.send_photo(reply_to_message_id=update.message.reply_to_message.message_id, chat_id=update.message.reply_to_message.chat.id, photo=fp, caption=message, parse_mode=ParseMode.MARKDOWN)

            else:

                forward_msg_result = await context.bot.send_photo(reply_to_message_id=dest_reply_to_message_id, chat_id=dest_channel, photo=fp, caption=message, parse_mode=ParseMode.MARKDOWN)
            
            await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])
        os.remove(file_name)

    except Exception as e:
        logger.error(f"Error replying message: {e}")



async def forward_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        print("***")
        print(update)
        print("***")
        print("Audio")
        print("***")

        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.caption

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.caption}
            """
        else:
            return

        file = await context.bot.get_file(update.message.audio.file_id)
        await file.download_to_drive(update.message.audio.file_id)
        file_name = update.message.audio.file_name
        os.rename(update.message.audio.file_id, file_name)

        with open(file_name, "rb") as fp:
            forward_msg_result = await context.bot.send_audio(chat_id=dest_channel, audio=fp , caption=message)
            await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

    except Exception as e:
        logger.error(f"Error replying message: {e}")

async def reply_forward_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        print("***")
        print(update)
        print("***")
        print("Audio")
        print("***")

        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.caption

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.caption}
            """
        else:
            return

        dest_reply_to_message_id = retrieve_conversation([update.message.chat.id,update.message.reply_to_message.message_id,dest_channel])

        file = await context.bot.get_file(update.message.audio.file_id)
        await file.download_to_drive(update.message.audio.file_id)
        file_name = update.message.audio.file_name
        os.rename(update.message.audio.file_id, file_name)

        with open(file_name, "rb") as fp:
            if dest_reply_to_message_id=="Conversation not found":
                forward_msg_result = await context.bot.send_audio(reply_to_message_id=update.message.reply_to_message.message_id, chat_id=update.message.reply_to_message.chat.id, audio=fp, caption=message)
            else:
                forward_msg_result = await context.bot.send_audio(reply_to_message_id=dest_reply_to_message_id, chat_id=dest_channel, audio=fp, caption=message)
                
            await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

        os.remove(file_name)


    except Exception as e:
        logger.error(f"Error replying message: {e}")




async def forward_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:

        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.caption

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.caption}
            """
        else:
            return

        if update.message.video is not None:
            file = await context.bot.get_file(update.message.video.file_id)
            await file.download_to_drive(update.message.video.file_id)
            file_name = update.message.video.file_name
            os.rename(update.message.video.file_id, file_name)

            with open(file_name, "rb") as fp:
                forward_msg_result = await context.bot.send_video(chat_id=dest_channel, video=fp , caption=message)
                await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

        elif update.message.document is not None:
            file = await context.bot.get_file(update.message.document.file_id)
            await file.download_to_drive(update.message.document.file_id)
            file_name = update.message.document.file_name
            os.rename(update.message.document.file_id, file_name)

            with open(file_name, "rb") as fp:
                forward_msg_result = await context.bot.send_document(chat_id=dest_channel, document=fp , caption=message)
                await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

        elif update.message.voice is not None:
            file = await context.bot.get_file(update.message.voice.file_id)
            await file.download_to_drive(update.message.voice.file_id)
            file_extension = update.message.voice.mime_type.rsplit('/', 1)
            file_name = update.message.voice.file_id + "." + file_extension[1]
            os.rename(update.message.voice.file_id, file_name)

            with open(file_name, "rb") as fp:
                forward_msg_result = await context.bot.send_voice(chat_id=dest_channel, voice=fp , caption=message)
                await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

        else:
            print("Unknown Attachment")


    except Exception as e:
        logger.error(f"Error replying message: {e}")

async def reply_forward_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:

        dest = await retrieve_channel_id(update.message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.message.from_user.first_name, update.message.from_user.last_name)

        if dest[1] == "1":
            message = update.message.caption

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.message.caption}
            """
        else:
            return

        dest_reply_to_message_id = retrieve_conversation([update.message.chat.id,update.message.reply_to_message.message_id,dest_channel])

        if update.message.video is not None:
            file = await context.bot.get_file(update.message.video.file_id)
            await file.download_to_drive(update.message.video.file_id)
            file_name = update.message.video.file_name
            os.rename(update.message.video.file_id, file_name)

            with open(file_name, "rb") as fp:
                if dest_reply_to_message_id=="Conversation not found":
                    forward_msg_result = await context.bot.send_video(reply_to_message_id=update.message.reply_to_message.message_id, chat_id=update.message.reply_to_message.chat.id, video=fp, caption=message)
                else:
                    forward_msg_result = await context.bot.send_video(reply_to_message_id=dest_reply_to_message_id, chat_id=dest_channel, video=fp, caption=message)
                await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

        elif update.message.document is not None:
            file = await context.bot.get_file(update.message.document.file_id)
            await file.download_to_drive(update.message.document.file_id)
            file_name = update.message.document.file_name
            os.rename(update.message.document.file_id, file_name)

            with open(file_name, "rb") as fp:
                if dest_reply_to_message_id=="Conversation not found":
                    forward_msg_result = await context.bot.send_document(reply_to_message_id=update.message.reply_to_message.message_id, chat_id=update.message.reply_to_message.chat.id, document=fp, caption=message)
                else:
                    forward_msg_result = await context.bot.send_document(reply_to_message_id=dest_reply_to_message_id, chat_id=dest_channel, document=fp, caption=message)
                await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

        elif update.message.voice is not None:

            file = await context.bot.get_file(update.message.voice.file_id)
            await file.download_to_drive(update.message.voice.file_id)
            file_extension = update.message.voice.mime_type.rsplit('/', 1)
            file_name = update.message.voice.file_id + "." + file_extension[1]
            os.rename(update.message.voice.file_id, file_name)

            with open(file_name, "rb") as fp:
                if dest_reply_to_message_id=="Conversation not found":
                    forward_msg_result = await context.bot.send_voice(reply_to_message_id=update.message.reply_to_message.message_id, chat_id=update.message.reply_to_message.chat.id, voice=fp, caption=message)
                else:
                    forward_msg_result = await context.bot.send_voice(reply_to_message_id=dest_reply_to_message_id, chat_id=dest_channel, voice=fp , caption=message)
                await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])

            os.remove(file_name)

        else:
            print("Unknown Attachment")

    except Exception as e:
        logger.error(f"Error replying message: {e}")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    if str(update.message.chat.id) == str(admin_group_id):
        await update.message.reply_text("Use /group_id to retrieve group id \n /list_group to list current group mapping \n /add_group_map to add group mapping \n /del_group_map to delete group mapping \n /db_size to view the db size")
    else:
        await update.message.reply_text("Use /group_id to retrieve group id")

async def group_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(update.message.chat.id)

async def list_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.chat.id) == str(admin_group_id):
        result = ""
        for key, value in groups_map.items():
            result += f"{key}: {value}\n"
        await update.message.reply_text(result)
    else:
        return

async def db_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.chat.id) == str(admin_group_id):
        db_stats = os.stat(dbfile)
        if db_stats.st_size > 1048576:
            await update.message.reply_text(f'DB Size is {db_stats.st_size / (1024 * 1024)}MB.')
        elif db_stats.st_size > 1024:
            await update.message.reply_text(f'DB Size is {db_stats.st_size / 1024}KB.')
        else:
            await update.message.reply_text(f'DB Size is {db_stats.st_size} Bytes.')
    else:
        return

async def add_group_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #await update.message.reply_text(update.message.chat.id)
    #await update.message.reply_text(admin_group_id)
    if str(update.message.chat.id) == str(admin_group_id):
        source_group = context.args[0] if context.args else 'empty_source_group'
        destination_group = context.args[1] if context.args else 'empty_destination_group'

        #await update.message.reply_text(update.message.chat.id)
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f'add_group_map_yes:{source_group}:{destination_group}'),
            InlineKeyboardButton("No", callback_data=f'add_group_map_no:{source_group}:{destination_group}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await update.message.reply_text(f'Are you sure want to map {source_group} with {destination_group}', reply_markup=reply_markup)

    else:
        return

async def del_group_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.chat.id) == str(admin_group_id):
        source_group = context.args[0] if context.args else 'empty_source_group'
        destination_group = context.args[1] if context.args else 'empty_destination_group'

        group_exist=check_group_mapping([source_group,destination_group])
        if group_exist == 1:
            keyboard = [
                [InlineKeyboardButton("Yes", callback_data=f'del_group_map_yes:{source_group}:{destination_group}'),
                InlineKeyboardButton("No", callback_data=f'del_group_map_no:{source_group}:{destination_group}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f'Are you sure want to delete mapping of {source_group} and {destination_group}', reply_markup=reply_markup)

        else:
            await update.message.reply_text(f'Failed to locate mapping of {source_group} and {destination_group}')
    else:
        return

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Parse the callback_data to extract the action and variable
    action, source_group, destination_group = query.data.split(':')
    
    # Handle responses based on the user's choice
    if action == 'add_group_map_yes':
        group_exist=check_group_mapping([source_group,destination_group])
        if group_exist == 1:
            await query.edit_message_text(text=f"Mapping of '{source_group}' with '{destination_group}' already exist.")

        elif group_exist == 2:
            await query.edit_message_text(text=f"'{source_group}' already had mapping with other group.")
        elif group_exist == 3:
            await query.edit_message_text(text=f"'{destination_group}' already had mapping with other group.")
        elif group_exist == 0:
            add_group_mapping_result = await add_group_mapping([source_group,destination_group])
            if add_group_mapping_result == 1:
                await query.edit_message_text(text=f"Map '{source_group}' with '{destination_group}' successfully.")
            elif add_group_mapping_result == 0:
                await query.edit_message_text(text=f"Failed to map '{source_group}' with '{destination_group}'.")
            else:
                await query.edit_message_text(text=f"Unknown error when try to map '{source_group}' with '{destination_group}'.")

        else:
            await query.edit_message_text(text=f"Unknown error, Please inform administrator.")

        # Here you can implement the logic to map the variable
    elif action == 'add_group_map_no':
        await query.edit_message_text(text=f"You choose not to map '{source_group}' with '{destination_group}'.")

    if action == 'del_group_map_yes':
        del_group_mapping_result = await del_group_mapping([source_group,destination_group,destination_group,source_group])
        if del_group_mapping_result == 1:
            await query.edit_message_text(text=f"Mapping of '{source_group}' and '{destination_group}' delete successfully.")
        else:
            await query.edit_message_text(text=f"Unknown error, Please inform administrator.")


    elif action == 'del_group_map_no':
        await query.edit_message_text(text=f"You choose not to delete mapping '{source_group}' and '{destination_group}'.")

async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    #print("#Edit Text#")
    #print(update)
    #print(update.edited_message.chat.id)
    #print(update.edited_message.chat)
    #print("#End Edit Text#")

    try:
        dest = await retrieve_channel_id(update.edited_message.chat.id)
        dest_channel = dest[0]

        sender = format_sender(update.edited_message.from_user.first_name, update.edited_message.from_user.last_name)

        if dest[1] == "1":
            message = update.edited_message.text

        elif dest[1] == "2":
            message = f"""
            *{sender}* \U0001F5E3 \n
            {update.edited_message.text}
            """
        else:
            return

        dest_reply_to_message_id=retrieve_conversation([update.edited_message.chat.id,update.edited_message.message_id,dest_channel])

        #print("###")
        #print(dest_reply_to_message_id)
        #print("###")

        if dest_reply_to_message_id=="Conversation not found":

            edit_msg_result = await context.bot.edit_message_text(message_id=update.edited_message.message_id,chat_id=update.edited_message.chat.id,text=message)
        
        else:
            
            edit_msg_result = await context.bot.edit_message_text(message_id=dest_reply_to_message_id,chat_id=dest_channel,text=message)
        
        #await add_conversation([update.message.chat.id,update.message.message_id,dest_channel,forward_msg_result.message_id])
    
    except Exception as e:
        logger.error(f"Error editing message: {e}")


def main():

        tbot = Application.builder().token(tg_bot_token).build()
        
        #tbot.add_handler(MessageHandler(filters.ALL, debug))
        tbot.add_handler(MessageHandler(filters.TEXT & filters.UpdateType.EDITED_MESSAGE, edit_text))
        
        tbot.add_handler(MessageHandler((filters.TEXT) & ~filters.COMMAND & ~filters.REPLY, forward_text))
        tbot.add_handler(MessageHandler((filters.TEXT) & ~filters.COMMAND & filters.REPLY, reply_forward_text))

        tbot.add_handler(MessageHandler((filters.PHOTO) & ~filters.COMMAND & ~filters.REPLY, forward_photo))
        tbot.add_handler(MessageHandler((filters.PHOTO) & ~filters.COMMAND & filters.REPLY, reply_forward_photo))

        tbot.add_handler(MessageHandler((filters.AUDIO) & ~filters.COMMAND & ~filters.REPLY, forward_audio))
        tbot.add_handler(MessageHandler((filters.AUDIO) & ~filters.COMMAND & filters.REPLY, reply_forward_audio))

        tbot.add_handler(MessageHandler((filters.ATTACHMENT) & ~filters.COMMAND & ~filters.REPLY, forward_attachment))
        tbot.add_handler(MessageHandler((filters.ATTACHMENT) & ~filters.COMMAND & filters.REPLY, reply_forward_attachment))

        tbot.add_handler(CommandHandler("help", help_handler))
        tbot.add_handler(CommandHandler("group_id", group_id))
        tbot.add_handler(CommandHandler("list_group", list_group))
        tbot.add_handler(CommandHandler("add_group_map", add_group_map))
        tbot.add_handler(CommandHandler("del_group_map", del_group_map))
        tbot.add_handler(CommandHandler("db_size", db_size))
        tbot.add_handler(CallbackQueryHandler(button_callback))

        tbot.add_handler(MessageHandler(filters.COMMAND, command_debug))

        #tbot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, forward_msg))
        #tbot.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video | Filters.document, forward_msg))
        #tbot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.REPLY, reply_msg))
        #tbot.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND & ~filters.REPLY, send_photo))
        
        #tbot.add_handler(MessageHandler(filters.Chat(chat_id=-997945969) & filters.TEXT & ~filters.COMMAND & ~filters.REPLY, group_997945969))
        #tbot.add_handler(MessageHandler(filters.Chat(chat_id=-997945969) & filters.TEXT & ~filters.COMMAND & ~filters.REPLY, reply_msg))

        #tbot.add_handler(MessageHandler(filters.ALL, debug))

        tbot.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Telegram Chat Bot is shutting down. Bye!")
        sys.exit(0)

