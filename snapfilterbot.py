import os
import keys
import tweepy
import time
from PySide2 import QtCore
from PySide2.QtWidgets import *
from PySide2.QtGui import *
import urllib.request
from PIL import Image
from PIL import ImageFilter
import cv2
import numpy as np
import json
import datetime


#api config
def api():
    auth = tweepy.OAuthHandler(keys.api_key, keys.api_secret)
    auth.set_access_token(keys.access_token, keys.access_token_secret)

    return tweepy.API(auth)


api = api()

try:
    api.verify_credentials()
    print("Connexion au compte Twitter réussie.")
    coStatus = "État de la connexion à Twitter : Réussi"
except:
    print("La connexion a échoué.")
    coStatus = "État de la connexion à Twitter : Échoué"


#création liste vérification déjà répondu
replied = []

#ouverture du fichier log et settings
log = open("log.txt", "a")
settings = open("settings.txt", "r+")

# réponse aux tweets
while True:

    readSettings = settings.read()
    now = datetime.datetime.now()
    print("----------\nActualisation... ||", now)
    # recherche de tweets
    max_tweets = 1500
    tweets = tweepy.Cursor(api.search_tweets, q="@SnapFilterBot basse qualité").items(max_tweets)
    for tweet in tweets:
        if tweet.id not in replied:

            #vérification follow
            friendship = api.get_friendship(source_id=tweet.user.id, target_id=1543665532121108482)
            isFollowing = json.dumps(friendship[0]._json).split(",")[3].split(":")[1].replace(" ", "")

            if "FollowNeededFalse" in readSettings:
                isFollowing = "true"

            if isFollowing == "true":
                try:
                    originalTweetId = tweet.in_reply_to_status_id_str
                    originalTweet = api.get_status(originalTweetId)
                except:
                    logtext = "----------\nTweet trouvé, ID "+ tweet.id_str+ "\n/!\ ERREUR : ce tweet n'est pas une réponse"
                    print(logtext)
                    log.write(logtext)
                    continue
                if 'media' in originalTweet.entities:
                    for image in originalTweet.entities['media']:

                        #récupération de l'image
                        mediaUrl = str(image['media_url'])
                        file_location = "images/temp/" + mediaUrl.rsplit('/', 1)[-1]
                        file_name = mediaUrl.rsplit('/', 1)[-1]
                        file_name = file_name.rsplit('.', 1)[0]
                        urllib.request.urlretrieve(image['media_url'], file_location)
                        logtext = "----------\nTweet trouvé, ID " + originalTweet.id_str + "\nURL de l'image : " + mediaUrl + "\nImage sauvegardée : " + file_location
                        print(logtext)
                        log.write(logtext)

                        # resize de l'image en 1080x1920
                        size = (1080, 1920)
                        image = Image.open(file_location)
                        img_w, img_h = image.size
                        ratio = 1080 / img_w
                        newWidth = int(img_w * ratio)
                        newHeight = int(img_h * ratio)
                        image = image.resize((newWidth, newHeight))
                        resizemodel = Image.new('RGBA', size, (0, 0, 0, 255))
                        resizemodel.paste(image, (int((size[0] - image.size[0]) / 2), int((size[1] - image.size[1]) / 2)))
                        resizemodel = resizemodel.filter(ImageFilter.GaussianBlur(radius=3))
                        resizemodel_location = "images/processing/" + file_name + ".png"
                        resizemodel.save(resizemodel_location)

                        #suppression de l'image Temp
                        os.remove(file_location)

                        # appliquage du filtre sur l'image traitée
                        filter = Image.open("images/filters/filtre1.png")
                        background = Image.open(resizemodel_location)
                        background.paste(filter, (0, 0), filter)
                        background_location = "images/post/" + file_name + ".png"
                        background.save(background_location, "PNG")

                        #suppression de l'image Process
                        os.remove(resizemodel_location)

                        #envoi de la réponse
                        media = api.media_upload(background_location)
                        postresult = api.update_status(status="Image en qualité snap :", in_reply_to_status_id=tweet.id_str, auto_populate_reply_metadata=True, media_ids=[media.media_id])
                        replied.append(tweet.id)

                        # suppression de l'image Post
                        os.remove(background_location)
                else:
                    logtext = "----------\nTweet trouvé, ID "+originalTweet.id_str+"\nTweet ignoré, aucune image détectée."
                    print(logtext)
                    log.write(logtext)

            else:
                logtext = "----------\nTweet trouvé, ID " + tweet.id_str + "\n/!\ L'utilisateur ne follow pas, mention ignorée"
                print(logtext)
                log.write(logtext)
        else:
            logtext = "----------\nTweet trouvé, ID "+originalTweet.id_str+"\n/!\ ERREUR : Déjà répondu !"
            print(logtext)
            log.write(logtext)

    time.sleep(30)


#fin du script