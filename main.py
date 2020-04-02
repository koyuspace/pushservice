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
loggedin = ""
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
    def on_notification(self, notification):
        if notification["type"] == "mention":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            user = notification["account"]["display_name"]
            if user == "":
                user = notification["account"]["username"]
            for mention in notification["status"]["mentions"]:
                device = str(r.get("koyuspace-app/device/"+mention["acct"])).replace("b'", "").replace("'", "")
                userdev = str(r.get("koyuspace-app/username/"+device)).replace("b'", "").replace("'", "")
                if userdev == mention["acct"]:
                    push_service = FCMNotification(api_key=fcm_token)
                    push_service.notify_single_device(registration_id=device, message_title=user+" mentioned you", message_body=toot, sound="Default")
                    print(mention["acct"]+"'s notification sent to "+device)
        if notification["type"] == "reblog":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            user = notification["account"]["display_name"]
            if user == "":
                user = notification["account"]["username"]
            device = str(r.get("koyuspace-app/device/"+notification["status"]["account"]["username"])).replace("b'", "").replace("'", "")
            userdev = str(r.get("koyuspace-app/username/"+device)).replace("b'", "").replace("'", "")
            if userdev == notification["status"]["account"]["username"]:
                push_service = FCMNotification(api_key=fcm_token)
                push_service.notify_single_device(registration_id=device, message_title=user+" boosted your hop", message_body=toot, sound="Default")
                print(notification["account"]["acct"]+"'s notification sent to "+device)
        if notification["type"] == "favourite":
            toot = str(html.document_fromstring(notification["status"]["content"]).text_content())
            user = notification["account"]["display_name"]
            if user == "":
                user = notification["account"]["username"]
            device = str(r.get("koyuspace-app/device/"+notification["status"]["account"]["username"])).replace("b'", "").replace("'", "")
            userdev = str(r.get("koyuspace-app/username/"+device)).replace("b'", "").replace("'", "")
            if userdev == notification["status"]["account"]["username"]:
                push_service = FCMNotification(api_key=fcm_token)
                push_service.notify_single_device(registration_id=device, message_title=user+" favourited your hop", message_body=toot, sound="Default")
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
    global loggedin
    if not mastodon.account_verify_credentials()["username"] in loggedin:
        listener = myListener()
        mastodon.stream_user(listener, run_async=True, reconnect_async=True, reconnect_async_wait_sec=5)
        print(mastodon.account_verify_credentials()["username"]+" registered with "+device+" and code "+code)
    r.set("koyuspace-app/codes", str(r.get("koyuspace-app/codes")).replace("b'", "").replace("'", "")+","+code)
    r.set("koyuspace-app/code/"+device, code)
    r.set("koyuspace-app/device/"+mastodon.account_verify_credentials()["username"], device)
    r.set("koyuspace-app/username/"+device, mastodon.account_verify_credentials()["username"])
    loggedin = loggedin+mastodon.account_verify_credentials()["username"]+","
    redirect(instance+"/web/timelines/home")

run(host='0.0.0.0', port=40040, server="tornado")