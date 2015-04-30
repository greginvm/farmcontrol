# Notes #

This is a special release of my FarmControl project for Zemanta. 

Some notes:

 - The app in currently not https enabled (the deployed app is used in local network)
 - The code listening to data on serial and sending data to the relay board is not separated from the app - should be
 - underscore.js is about to be removed and replaced with jQuery functions
 - js code is located in app/static/custom/
 - the app is a personal project so don't expect anything fancy, there are some shortcuts and some weird things (DB stuff) 
 
The default user/pass: admin/admin

By default random values are generated for sensor values and they can go pretty wild, in development mode
the dat.gui floating menu is enabled and you can use it to set a value for a sensor over there.

If you want to test SMS/Calls you need Twilio API access keys - register at twilio.com and you get an API key with which
 you can send SMS-es to Slovenia for free (until you are a trial user and only to confirmed phone numbers).


# Install #

## 1. RRDtool ##


    sudo apt-get install libcairo2-dev libxml2-dev libpango1.0-dev librrd-dev
    sudo apt-get install rrdtool
    
    
## 2. Python libs ##

    
    pip install -r requirements/requirements.txt
    
    
## 3. JS libs ##

Go to app/ and then:

    bower install bower.json
    

## Initialization and startup ##

All paths are relative to project root.

1. Create "instance" and "db" folders (by default "db" folder is used for the sqlite database, instance folder for
custom config files). Both folders are set to be ignored by git
2. Install secret key
    
    head -c 24 /dev/urandom > instance/secret_key
    
3. setup dev database

    python manage.py create_db
    python manage.py dev_data    # add some test data
    
4. run

    python manage.py runserver
    
5. go to localhost:5000