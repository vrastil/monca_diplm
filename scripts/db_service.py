""" manage database -- create, update """

from __future__ import print_function
import os
import sys
import pymongo
from getpass import getpass
import datetime
import ipywidgets as widgets
from IPython.display import display

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import calendar
import csv

TRANSLATE = {
    'stav_end' : 'stav ke konci roku',
    'stav_start' : 'stav na začátku roku',
    'mrtve_nar_mlad' : 'mrtvě narozená mláďata',
    'zive_nar_mlad' : 'živě narozená mláďata',
    'uhyn_do_5d' : 'úhyn do 5 dnů',
    'uhyn_do_3m' : 'úhyn do 3 měsíců',
    'uhyn_do_12m' : 'úhyn do 12 měsíců',
    'porody' : 'porody',
    'odchov' : 'odchov'
}

OUT_OPT_DEF = {
    'dir' : '/home/michal/Dropbox/Diplomka Monca/img_py/'
}

SETTINGS_ROCENKY = [
    'Druh',
    'Zoo',
    'Rok',
    {'stav_start' : 'samec'},
    {'stav_start' : 'samice'},
    {'stav_start' : 'nezname'},
    {'prichod' : 'samec'},
    {'prichod' : 'samice'},
    {'prichod' : 'nezname'},
    {'odchody' : 'samec'},
    {'odchody' : 'samice'},
    {'odchody' : 'nezname'},
    {'uhyn' : 'samec'},
    {'uhyn' : 'samice'},
    {'uhyn' : 'nezname'},
    {'jine_ubytky' : 'samec'},
    {'jine_ubytky' : 'samice'},
    'potraty',
    'porody',
    'uhyn_grav_samic',
    {'mrtve_nar_mlad' : 'samec'},
    {'mrtve_nar_mlad' : 'samice'},
    {'mrtve_nar_mlad' : 'nezname'},
    {'zive_nar_mlad' : 'samec'},
    {'zive_nar_mlad' : 'samice'},
    {'zive_nar_mlad' : 'nezname'},
    {'uhyn_do_5d' : 'samec'},
    {'uhyn_do_5d' : 'samice'},
    {'uhyn_do_5d' : 'nezname'},
    {'uhyn_do_3m' : 'samec'},
    {'uhyn_do_3m' : 'samice'},
    {'uhyn_do_3m' : 'nezname'},
    {'uhyn_do_12m' : 'samec'},
    {'uhyn_do_12m' : 'samice'},
    {'uhyn_do_12m' : 'nezname'},
    {'odchody2' : 'samec'},
    {'odchody2' : 'samice'},
    {'odchody2' : 'nezname'},
    {'odchov' : 'samec'},
    {'odchov' : 'samice'},
    {'odchov' : 'nezname'},
    {'deponace' : 'samec'},
    {'deponace' : 'samice'},
    {'deponace' : 'nezname'},
    {'stav_end' : 'samec'},
    {'stav_end' : 'samice'},
    {'stav_end' : 'nezname'},
]

SETTINGS_KNIHY = [
    'cislo',
    'pohlaví',
    'jmeno',
    'narozen_datum',
    'narozen_misto',
    'prichod_DK',
    {'vek' : 'rok'},
    {'vek' : 'mesic'},
    {'vek' : 'dny'},
    'odchod_datum',
    'odchod_zoo',
    'poznamka',
    {'rodice' : 'samec'},
    {'rodice' : 'samice'},
]

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

def plot_basic(data, suptitle="", out_opt=None, bar=False):
    fig = plt.figure(figsize=(14,10))
    ax = plt.gca()

    i = 0
    width = 0.8/len(data)
    for item, val in data.items():
        val = np.array(val)
        x = val[:,0]
        y = val[:,1]
        if not bar:
            ax.plot(x, y, 'o-', label=item)
        else:
            x = x - 0.8 + width*i
            ax.bar(x, y, width, label=item)
            i += 1

    ax.legend()
    fig.suptitle(suptitle, size=30, y=0.94)
    plt.show()
    filename = out_opt['dir'] + out_opt['filename']
    fig.savefig(filename, format="png")

def plot_all_zoo_rok(db, druh, cat, out_opt=None):
    query = {
        'Druh' : druh,
    }

    proj = {
        '_id' : 0,
        'Rok' : 1,
        'Zoo' : 1,
        cat : 1
    }

    my_data = {}

    for doc in db.find(query, proj):
        zoo = doc['Zoo']
        rok = doc['Rok']
        narozeny = sum(list(doc[cat].values()))
        
        if zoo not in my_data:
            my_data[zoo] = []
        my_data[zoo].append([rok, narozeny])

    # plot
    if out_opt is None:
        out_opt = OUT_OPT_DEF
    suptitle = druh + ' (' + TRANSLATE[cat] + ')'
    out_opt['filename'] = druh.replace(' ', '_') + '_' + cat.replace(' ', '_') + '.png'
    plot_basic(my_data, suptitle, out_opt=out_opt)


def plot_one_zoo_rok(db, druh, zoo, cats, out_opt=None, **kwargs):
    query = {
        'Druh' : druh,
        'Zoo' : zoo
    }

    proj = {
        '_id' : 0,
        'Rok' : 1,
    }
    for cat in cats:
        proj[cat] = 1

    my_data = {TRANSLATE[cat] : [] for cat in cats}

    for doc in db.find(query, proj):
        rok = doc['Rok']
        for cat in cats:
            if isinstance(doc[cat], dict):
                pocet = sum(list(doc[cat].values()))
            else:
                pocet = doc[cat]
            my_data[TRANSLATE[cat]].append([rok, pocet])

    # plot
    if out_opt is None:
        out_opt = OUT_OPT_DEF

    suptitle = druh + ', ' + zoo + ' (' + out_opt['suptitle'] + ')'
    out_opt['filename'] = druh.replace(' ', '_') + '_' + zoo.replace(' ', '_') + '_' + out_opt['suptitle'].replace(' ', '_') + '.png'
    if 'bar' in kwargs and kwargs['bar']:
        out_opt['filename'] = out_opt['filename'].replace('.png', '_' + ''.join([x[0] for x in cats]) + '_bar.png')
    plot_basic(my_data, suptitle, out_opt=out_opt, **kwargs)


def plot_cats_rok(db, druh, cats, out_opt=None):
    if druh is not None:
        query = {
            'Druh' : druh,
        }
    else:
        query = {}
        druh = 'Všechny druhy'

    proj = {
        '_id' : 0,
        'Rok' : 1,
    }
    for cat in cats:
        proj[cat] = 1

    my_data = {TRANSLATE[cat] : [] for cat in cats}

    all_doc = list(db.find(query, proj))
    roky = sorted(set([doc['Rok'] for doc in all_doc]))

    for cat in cats:
        my_data[TRANSLATE[cat]] = [[rok, 0] for rok in roky]

    for doc in all_doc:
        rok = doc['Rok']
        for cat in cats:
            pocet = sum(list(doc[cat].values()))
            item = next(x for x in my_data[TRANSLATE[cat]] if x[0] == rok)
            item[1] += pocet

    # plot
    if out_opt is None:
        out_opt = OUT_OPT_DEF

    suptitle = druh + ' (' + out_opt['suptitle'] + ')'
    out_opt['filename'] = druh.replace(' ', '_') + '_' + out_opt['suptitle'].replace(' ', '_') + '.png'
    plot_basic(my_data, suptitle, out_opt=out_opt)


def create_table(filename, coll, *cats):

    druhy = coll.distinct('Druh')
    roky = sorted(coll.distinct('Rok'))
    csv_file = OUT_OPT_DEF["dir"] + 'tables/' + filename
            
    with open(csv_file, mode='w') as a_file:
        csv_writer = csv.writer(a_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # hlavicka
        csv_writer.writerow([''] + roky)
        
        # jednotlive druhy
        for druh in druhy:
            row = [druh]
            # get all data
            match = [{cat : {"$gt" : 0}} for cat in cats]
            group = {cat.replace('.', '@') : {"$sum" : "$" + cat} for cat in cats}
            group["_id"] = "$Rok"
            group["Pocet ZOO"] = {"$sum" : 1}
            my_data = list(coll.aggregate([
                    {"$match"  : {"Druh" : druh, "$or" : match}},
                    {"$group" : group}
                    ]))

            # prochazej vzestupne po letetcj
            for rok in roky:
                # kdyz existuje zaznam, uloz ho
                try:
                    item = next(x for x in my_data if x['_id'] == rok)
                    rec = ""
                    for cat in cats:
                        key = cat.replace('.', '@')
                        rec +=  "%i." % item[key]

                    rec = rec[:-1] + " (%i)" % item['Pocet ZOO']
                    row.append(rec)
                    
                # kdyz ne, vypln prazdny zaznam
                except:
                    row.append('')

            # print(item[key])
                    
            # write only non-empty rows
            if [x for x in row[1:] if x]:
                csv_writer.writerow(row)

def get_num_from_str(rec):
    if rec:
        return int(rec)
    else:
        return 0

def import_data(coll, a_file, settings, str_list, druh=None):
    # get data from csv file
    with open(a_file) as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        all_data = [row for row in spamreader if row[0] != '']

    all_data_dict = []
    # projdi vsechny radky
    for row in all_data:
        new_row = {}
        # projdi vsechny zaznamy
        for i, rec in enumerate(row):
            key = settings[i]
            # str list, zbytek cisla
            if i in str_list:
                new_row[key] = rec
            else:
                # primo zaznam
                if isinstance(key, str):
                    new_row[key] = get_num_from_str(rec)
                # kategorie v zaznamu
                else:
                    key, sub_key = list(key.items())[0]
                    if key not in new_row:
                        new_row[key] = {}
                    new_row[key][sub_key] = get_num_from_str(rec)
            
        # pridej info o druhu
        if druh is not None and 'Druh' not in settings:
            new_row['Druh'] = druh

        # uloz dict
        all_data_dict.append(new_row)

    # insert data and get info
    res = coll.insert_many(all_data_dict)
    print("Vlozeno %i zaznamu." % len(res.inserted_ids))

def get_name(coll, cislo):
    return coll.find_one({"cislo" : cislo})["jmeno"]

def transformuj_datum(datum, form_in=None, form_out=None):
    if form_in is None:
        form_in = '%m/%d/%Y'

    if form_out is None:
        form_out = '%d.%m.%Y'

    # prazdne stringy netransformuj
    if datum:
        # dostan datetime
        date = datetime.datetime.strptime(datum, form_in)

        # preved zas na string
        datum = date.strftime(form_out)

    return datum

def get_otce(coll):
    match = {'rodice.samec' : {"$gt" : 0}}
    group = {
        "_id" : "$rodice.samec",
        "pocet_potomku" : {"$sum" : 1},
        "potomci" : {"$push" : {
            "cislo" : "$cislo",
            "jmeno" : "$jmeno",
            "vek" : "$vek",
            "matka" : "$rodice.samice",
            "pohlavi" : "$pohlaví",
            "narozen" : "$narozen_datum",
            "odchod" : "$odchod_datum",
            "poznamka" : "$poznamka"
        }}
    }

    data = list(coll.aggregate([
        {"$match" : match},
        {"$group" : group}
    ]))
    
    # jmeno otce
    for otec in data:
        otec["jmeno"] = get_name(coll, otec["_id"])
        for pot in otec["potomci"]:
            # pridej jmeno matky
            pot["matka"] = get_name(coll, pot["matka"])
            # transformuj data
            pot["narozen"] = transformuj_datum(pot["narozen"])
            pot["odchod"] = transformuj_datum(pot["odchod"])
    
    return data

def create_table_potomstva(coll, filename, otci):
    csv_file = OUT_OPT_DEF["dir"] + 'tables/' + filename
    
    with open(csv_file, mode='w') as a_file:
        csv_writer = csv.writer(a_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        for otec in otci:
            csv_writer.writerow([otec["jmeno"]])
            csv_writer.writerow([])
            
            # hlavicka
            row = ['cislo', 'pohlavi', 'rok', 'mesic', 'dny'] 
            row += [x for x in otec["potomci"][0].keys() if x not in row if x != 'vek']
            csv_writer.writerow(row)
            
            for pot in otec["potomci"]:
                row = [pot.pop('cislo'), pot.pop('pohlavi')]
                vek = pot.pop('vek')
                row += vek.values()
                for val in pot.values():
                    row.append(val)
                    
                csv_writer.writerow(row)
                
            # 2 blank rows
            csv_writer.writerow([])
            csv_writer.writerow([])