# -*- coding: utf-8 -*-
#
#     Author : Suphakit Annoppornchai
#     Date   : Apr 8 2017
#     Name   : line bot
#
#          https://saixiii.ddns.net
# 
# Copyright (C) 2017  Suphakit Annoppornchai
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.

from __future__ import unicode_literals

import sys
import os
import json
import errno
import time
import thread
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from time import strftime
from argparse import ArgumentParser
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)

#-------------------------------------------------------------------------------
#     G L O B A L    V A R I A B L E S
#-------------------------------------------------------------------------------

botname = 'Saixiii'
botcall = '-'
botlen  = len(botcall)

processpool = 5

# get channel_secret and channel_access_token from your environment variable
channel_secret = '
channel_access_token =
signature = ''

# Log file configuration
static_tmp_path = '/app/python/Line/log/content'
chat_file = '/app/python/Line/log/' + botname + '.msg'
app_file = '/app/python/Line/log/' + botname + '.log'
log_size = 1024 * 1024 * 10
log_backup = 50
log_format = '[%(asctime)s] [%(levelname)s] - %(message)s'
log_mode = logging.DEBUG

# Kafka configuration
kafka_topic = 'line-saixiii'
kafka_ip = 'saixiii.ddns.net'
kafka_port = '9092'

#-------------------------------------------------------------------------------
#     I N I T I A L    P R O G R A M
#-------------------------------------------------------------------------------

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

#-------------------------------------------------------------------------------
#     F U N C T I O N S
#-------------------------------------------------------------------------------

# convert epoch date to date time
def convert_epoch(epoch):
  sec = float(epoch) / 1000
  dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(sec))
  return str(dt)

# Function check call bot
def chkcall(msg):
	if msg != None and msg[:botlen].lower() == botcall:
		return True
	else:
		return False

# function for create tmp dir for download content
def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise
            

# create logger moule
def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter(log_format)
    fileHandler = RotatingFileHandler(log_file, maxBytes=log_size, backupCount=log_backup)
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)

# get source id of user, group, room
def get_sourceid(event):
    if isinstance(event.source, SourceUser):
      profile = line_bot_api.get_profile(event.source.user_id)
      return profile.user_id
    elif isinstance(event.source, SourceGroup):
    	return event.source.group_id
    elif isinstance(event.source, SourceRoom):
    	return event.source.room_id
    	
   
# push message
def reply_message(event,msg):
    if isinstance(event.source, SourceUser):
      profile = line_bot_api.get_profile(event.source.user_id)
      line_bot_api.push_message(profile.user_id, TextSendMessage(text=msg))
    elif isinstance(event.source, SourceGroup):
    	line_bot_api.push_message(event.source.group_id, TextSendMessage(text=msg))
    elif isinstance(event.source, SourceRoom):
    	line_bot_api.push_message(event.source.room_id, TextSendMessage(text=msg))



@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    msg = event.message.text
    if not chkcall(msg): return
    msg = msg[len(msg.split(' ', 1)[0])+1:]
    if msg == 'profile':
        if isinstance(event.source, SourceUser):
            profile = line_bot_api.get_profile(event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(
                        text='Display name: ' + profile.display_name
                    ),
                    TextSendMessage(
                        text='Status message: ' + profile.status_message
                    )
                ]
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="Bot can't use profile API without user ID"))
    elif msg == 'bye':
        if isinstance(event.source, SourceGroup):
            line_bot_api.reply_message(
                event.reply_token, TextMessage(text='Leaving group'))
            line_bot_api.leave_group(event.source.group_id)
        elif isinstance(event.source, SourceRoom):
            line_bot_api.reply_message(
                event.reply_token, TextMessage(text='Leaving group'))
            line_bot_api.leave_room(event.source.room_id)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="Bot can't leave from 1:1 chat"))
    elif msg == 'confirm':
        confirm_template = ConfirmTemplate(text='Do it?', actions=[
            MessageTemplateAction(label='Yes', text='Yes!'),
            MessageTemplateAction(label='No', text='No!'),
        ])
        template_message = TemplateSendMessage(
            alt_text='Confirm alt text', template=confirm_template)
        line_bot_api.reply_message(event.reply_token, template_message)
    elif msg == 'buttons':
        buttons_template = ButtonsTemplate(
            title='My buttons sample', text='Hello, my buttons', actions=[
                URITemplateAction(
                    label='Go to line.me', uri='https://line.me'),
                PostbackTemplateAction(label='ping', data='ping'),
                PostbackTemplateAction(
                    label='ping with text', data='ping',
                    text='ping'),
                MessageTemplateAction(label='Translate Rice', text='米')
            ])
        template_message = TemplateSendMessage(
            alt_text='Buttons alt text', template=buttons_template)
        line_bot_api.reply_message(event.reply_token, template_message)
    elif msg == 'carousel':
        carousel_template = CarouselTemplate(columns=[
            CarouselColumn(text='hoge1', title='fuga1', actions=[
                URITemplateAction(
                    label='Go to line.me', uri='https://line.me'),
                PostbackTemplateAction(label='ping', data='ping')
            ]),
            CarouselColumn(text='hoge2', title='fuga2', actions=[
                PostbackTemplateAction(
                    label='ping with text', data='ping',
                    text='ping'),
                MessageTemplateAction(label='Translate Rice', text='米')
            ]),
        ])
        template_message = TemplateSendMessage(
            alt_text='Buttons alt text', template=carousel_template)
        line_bot_api.reply_message(event.reply_token, template_message)
    elif msg == 'id':
        msg = event.source.type + ':' + get_sourceid(event)
        line_bot_api.push_message(get_sourceid(event), TextMessage(text=msg))
    elif msg:
        line_bot_api.push_message(get_sourceid(event), TextMessage(text=msg))


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        LocationSendMessage(
            title=event.message.title, address=event.message.address,
            latitude=event.message.latitude, longitude=event.message.longitude
        )
    )


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id)
    )


# Other Message Type
#@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '.' + ext
    dist_name = os.path.basename(dist_path)
    os.rename(tempfile_path, dist_path)

    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(text='Save content.'),
            TextSendMessage(text=request.host_url + os.path.join('static', 'content', dist_name))
        ])


@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text='Got follow event'))


@handler.add(UnfollowEvent)
def handle_unfollow():
    app.logger.info("Got Unfollow event")


@handler.add(JoinEvent)
def handle_join(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='Joined this ' + event.source.type))


@handler.add(LeaveEvent)
def handle_leave():
    app.logger.info("Got leave event")


@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data == 'ping':
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='pong'))


@handler.add(BeaconEvent)
def handle_beacon(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='Got beacon event. hwid=' + event.beacon.hwid))


def main():
    
    setup_logger('app', app_file, log_mode)
    setup_logger('chat', chat_file)
    app = logging.getLogger('app')
    chat = logging.getLogger('chat')

    # create tmp dir for download content
    make_static_tmp_dir()
    
    # create kafka consumer instance
    consumer = KafkaConsumer(kafka_topic,group_id=botname,bootstrap_servers=[kafka_ip + ':' + kafka_port],value_deserializer=lambda m: json.loads(m.decode('utf-8')))
    
    # consuming data
    try:
        for message in consumer:
          app.debug("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                                message.offset, message.key,
                                                message.value))
          chat.info(message.value)
          body = json.dumps(message.value, ensure_ascii=False)
          thread.start_new_thread(handler.handle,(body,signature,))
          
    except KafkaError as e:
        app.error('kafka error %s: %s' % (str(e), type(e)))
    except Exception as e:
        app.error('exception %s: %s' % (str(e), type(e)))
        raise
    	
    # run
    
    
    
    
if '__main__' == __name__:
    main()