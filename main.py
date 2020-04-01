#!/usr/bin/python3
# -*- coding: utf-8 -*-

from mastodon import Mastodon, StreamListener
from lxml import html
from pyfcm import FCMNotification
from bottle import * # pylint: disable=unused-wildcard-import
import redis
import os

instance = "https://koyu.space"
pushservice = "https://pushservice.koyu.space"
fcm_token = os.environ["FCM_TOKEN"]
r = redis.Redis(host='localhost', port=6379, db=0)

if not os.path.exists("clientcred"):
    Mastodon.create_app(
        "koyu.space App",
        api_base_url = instance,
        to_file = "clientcred",
        scopes=['read', 'write', 'follow', 'push'],
        redirect_uris=pushservice+"/callback"
    )

mastodon = Mastodon(
    client_id = "clientcred",
    api_base_url = instance
)

f = open("clientcred", "r")
ccred = f.readlines()
f.close()

class myListener(StreamListener):
    def on_notification(self, notification, username):
        if notification["type"] == "mention":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            user = notification["account"]["display_name"]
            for mention in notification["status"]["mentions"]:
                device = str(r.get("koyuspace-app/device/"+mention["acct"])).replace("b'", "").replace("'", "")
                push_service = FCMNotification(api_key=fcm_token)
                push_service.notify_single_device(registration_id=device, message_title=user+" mentioned you", message_body=toot)
                print(mention["acct"]+"'s notification sent to "+device)
        if notification["type"] == "reblog":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            user = notification["account"]["display_name"]
            device = str(r.get("koyuspace-app/device/"+username)).replace("b'", "").replace("'", "")
            push_service = FCMNotification(api_key=fcm_token)
            push_service.notify_single_device(registration_id=device, message_title=user+" boosted your hop", message_body=toot)
            print(notification["account"]["acct"]+"'s notification sent to "+device)
        if notification["type"] == "favourite":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            user = notification["account"]["display_name"]
            device = str(r.get("koyuspace-app/device/"+username)).replace("b'", "").replace("'", "")
            push_service = FCMNotification(api_key=fcm_token)
            push_service.notify_single_device(registration_id=device, message_title=user+" favourited your hop", message_body=toot)
            print(notification["account"]["acct"]+"'s notification sent to "+device)
        if notification["type"] == "follow":
            user = notification["account"]["display_name"]
            device = str(r.get("koyuspace-app/device/"+username)).replace("b'", "").replace("'", "")
            push_service = FCMNotification(api_key=fcm_token)
            push_service.notify_single_device(registration_id=device, message_title="Someone followed you", message_body=user+" followed you")
            print(notification["account"]["acct"]+"'s notification sent to "+device)
        if notification["type"] == "follow_request":
            user = notification["account"]["display_name"]
            device = str(r.get("koyuspace-app/device/"+username)).replace("b'", "").replace("'", "")
            push_service = FCMNotification(api_key=fcm_token)
            push_service.notify_single_device(registration_id=device, message_title="Someone sent a follow request", message_body=user+" sent a follow request to you")
            print(notification["account"]["acct"]+"'s notification sent to "+device)
        if notification["type"] == "poll":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            device = str(r.get("koyuspace-app/device/"+username)).replace("b'", "").replace("'", "")
            push_service = FCMNotification(api_key=fcm_token)
            push_service.notify_single_device(registration_id=device, message_title="A poll has ended", message_body=toot)
            print(notification["account"]["acct"]+"'s notification sent to "+device)

@get("/register")
def register():
    device = request.query['device'] # pylint: disable=unsubscriptable-object
    code = str(r.get("koyuspace-app/code/"+device)).replace("b'", "").replace("'", "")
    try:
        mastodon.log_in(code=code, redirect_uri=pushservice+"/callback?device="+device, scopes=['read', 'write', 'follow', 'push'])
        print(mastodon.account_verify_credentials()["username"]+" logged in with "+device+" and code "+code)
        redirect(instance+"/web/timelines/home")
    except:
        url = mastodon.auth_request_url(client_id="clientcred", redirect_uris=pushservice+"/callback?device="+device, scopes=['read', 'write', 'follow', 'push'], force_login=False)
        redirect(url)

@get("/callback")
def callback():
    device = request.query['device'] # pylint: disable=unsubscriptable-object
    code = request.query['code'] # pylint: disable=unsubscriptable-object
    mastodon.log_in(code=code, redirect_uri=pushservice+"/callback?device="+device, scopes=['read', 'write', 'follow', 'push'])
    listener = myListener(username=mastodon.account_verify_credentials()["username"])
    mastodon.stream_user(listener, run_async=True)
    print(mastodon.account_verify_credentials()["username"]+" registered with "+device+" and code "+code)
    r.set("koyuspace-app/codes", str(r.get("koyuspace-app/codes")).replace("b'", "").replace("'", "")+","+code)
    r.set("koyuspace-app/code/"+device, code)
    r.set("koyuspace-app/device/"+mastodon.account_verify_credentials()["username"], device)
    redirect(instance+"/web/timelines/home")

run(host='0.0.0.0', port=40040, server="tornado")