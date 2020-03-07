""" manage database -- create, update """

from __future__ import print_function
import os
import sys
import pymongo
from getpass import getpass


def create_database(host='localhost', port=27017, user='admin'):
    """create database and user admin in it,
    databse should be started without authentication this first time"""

    print("Database server should be running without authentication on host '%s' and port '%i'" % (
        host, port))
    input("Press Enter to continue...")
    client = pymongo.MongoClient(host, port)
    db = client['admin']
    try:
        user = input("Username (default '%s'):" % user) or user
        db.command("createUser", user, pwd=getpass(prompt='Password:'), roles=[{'role':'userAdminAnyDatabase','db':'admin'}, "readWriteAnyDatabase"])
    except pymongo.errors.DuplicateKeyError as e:
        print(e)
    else:
        print("User '%s' successfully created. Restart the server with authentication enabled." % user)


def connect_db(host='localhost', port=27017, user='admin'):
    for _ in range(3):
        try:
            client = pymongo.MongoClient(host, port, username=user, password=getpass(prompt='Password:'))
            client['admin'].list_collection_names()
        except pymongo.errors.OperationFailure as e:
            print(e)
        else:
            print("Successfully conected to the database.")
            return client

def print_unique(db, field):
    xx = sorted(db.distinct(field, {}))
    print(field + ' (' + str(len(xx)) + '):')
    for x in xx:
        print('\t', x)



