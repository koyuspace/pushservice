#!/usr/bin/python3
# -*- coding: utf-8 -*-

from mastodon import Mastodon, StreamListener
from lxml import html
from pyfcm import FCMNotification
from bottle import * # pylint: disable=unused-wildcard-import
import redis
import os

f = open("pid", "w")
f.write(str(os.getpid()))
f.close()

instance = "https://koyu.space"
pushservice = "https://pushservice.koyu.space"
fcm_token = os.environ["FCM_TOKEN"]
loggedin = ""
REDIS_HOST = "localhost"
if "REDIS_HOST" in os.environ:
    REDIS_HOST = os.environ["REDIS_HOST"]
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

if not os.path.exists("clientcred"):
    Mastodon.create_app(
        "koyu.space for Android",
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
    def on_notification(self, notification):
        try:
            if notification["type"] == "mention":
                toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
                user = notification["account"]["display_name"]
                if user == "":
                    user = notification["account"]["username"]
                for mention in notification["status"]["mentions"]:
                    device = str(r.get("koyuspace-app/device/"+mention["acct"])).replace("b'", "").replace("'", "")
                    push_service = FCMNotification(api_key=fcm_token)
                    push_service.notify_single_device(registration_id=device, message_title=user+" mentioned you", message_body=toot, sound="mention")
                    print(mention["acct"]+"'s notification sent to "+device)
            if notification["type"] == "posted":
                toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
                user = notification["account"]["display_name"]
                if user == "":
                    user = notification["account"]["username"]
                device = str(r.get("koyuspace-app/device/"+notification["status"]["account"]["username"])).replace("b'", "").replace("'", "")
                push_service = FCMNotification(api_key=fcm_token)
                push_service.notify_single_device(registration_id=device, message_title=user+" just posted", message_body=toot, sound="mention") # Use mention sound here, because we don't have much sounds in the app
            if notification["type"] == "reblog":
                toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
                user = notification["account"]["display_name"]
                if user == "":
                    user = notification["account"]["username"]
                device = str(r.get("koyuspace-app/device/"+notification["status"]["account"]["username"])).replace("b'", "").replace("'", "")
                push_service = FCMNotification(api_key=fcm_token)
                push_service.notify_single_device(registration_id=device, message_title=user+" boosted your hop", message_body=toot, sound="boost")
                print(notification["account"]["acct"]+"'s notification sent to "+device)
            if notification["type"] == "favourite":
                toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
                user = notification["account"]["display_name"]
                if user == "":
                    user = notification["account"]["username"]
                device = str(r.get("koyuspace-app/device/"+notification["status"]["account"]["username"])).replace("b'", "").replace("'", "")
                push_service = FCMNotification(api_key=fcm_token)
                push_service.notify_single_device(registration_id=device, message_title=user+" favourited your hop", message_body=toot, sound="favourite")
                print(notification["account"]["acct"]+"'s notification sent to "+device)
        except:
            pass

@get("/register")
def register():
    device = request.query['device'] # pylint: disable=unsubscriptable-object
    username = str(r.get("koyuspace-app/username/"+device)).replace("b'", "").replace("'", "")
    global loggedin
    if username in loggedin:
        redirect(instance+"/web/timelines/home")
    else:
        url = mastodon.auth_request_url(client_id="clientcred", redirect_uris=pushservice+"/callback?device="+device, scopes=['read', 'write', 'follow', 'push'], force_login=False)
        redirect(url)

@get("/callback")
def callback():
    device = request.query['device'] # pylint: disable=unsubscriptable-object
    code = request.query['code'] # pylint: disable=unsubscriptable-object
    mastodon.log_in(code=code, redirect_uri=pushservice+"/callback?device="+device, scopes=['read', 'write', 'follow', 'push'])
    ddevice = str(r.get("koyuspace-app/device/"+mastodon.account_verify_credentials()["username"])).replace("b'", "").replace("'", "")
    global loggedin
    if not mastodon.account_verify_credentials()["username"] in loggedin:
        if device != "null":
            listener = myListener()
            mastodon.stream_user(listener, run_async=True, reconnect_async=True, reconnect_async_wait_sec=5)
            print(mastodon.account_verify_credentials()["username"]+" registered with "+device+" and code "+code)
    if device != ddevice:
        if device != "null":
            listener = myListener()
            mastodon.stream_user(listener, run_async=True, reconnect_async=True, reconnect_async_wait_sec=5)
            print(mastodon.account_verify_credentials()["username"]+" registered with "+device+" and code "+code)
    r.set("koyuspace-app/codes", str(r.get("koyuspace-app/codes")).replace("b'", "").replace("'", "")+","+code)
    r.set("koyuspace-app/code/"+device, code)
    r.set("koyuspace-app/device/"+mastodon.account_verify_credentials()["username"], device)
    r.set("koyuspace-app/username/"+device, mastodon.account_verify_credentials()["username"])
    loggedin = loggedin+mastodon.account_verify_credentials()["username"]+","
    if device != "null":
        redirect(instance+"/web/timelines/home")
    else:
        redirect("/retry")

@get("/retry")
def retry():
    return "<h1 style=\"text-align:center\">Token authorization failed. Please restart the app to try again.</h1>"

run(host='0.0.0.0', port=40040, server="tornado")
