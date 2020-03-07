from __future__ import print_function

import datetime

import xlsx_manipulation as xls

def create_table(coll, cats):

    druhy = coll.distinct('Druh')
    roky = sorted(coll.distinct('Rok'))
    data = []
            
    # hlavicka
    data.append([''] + roky)
    
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

        # prochazej vzestupne po letetch
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
                
        # write only non-empty rows
        if [x for x in row[1:] if x]:
            data.append(row)

    return data

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

def get_name(coll, druh, ZOO, cislo):
    return coll.find_one({"Druh" : druh, "ZOO" : ZOO, "číslo" : cislo})["jméno"]

def transformuj_datum(datum, form_in=None, form_out=None):
    if form_in is None:
        form_in = '%m/%d/%Y'

    if form_out is None:
        form_out = '%d.%m.%Y'

    # prazdne stringy netransformuj
    if datum:
        # dostan datetime
        if isinstance(datum, str):
            date = datetime.datetime.strptime(datum, form_in)
        else:
            date = datum

        # preved zas na string
        datum = date.strftime(form_out)

    return datum

def get_otce(coll, druh, ZOO):
    match = {'ZOO' : ZOO, 'Druh' : druh, 'Rodiče.Samec' : {"$gt" : 0}}
    group = {
        "_id" : "$Rodiče.Samec",
        "pocet_potomku" : {"$sum" : 1},
        "potomci" : {"$push" : {
            "cislo" : "$číslo",
            "jmeno" : "$jméno",
            "vek" : "$věk",
            "matka" : "$Rodiče.Samice",
            "pohlavi" : "$pohlaví",
            "narozen" : "$narozen",
            "odchod" : "$odchod",
            "poznamka" : "$poznámka"
        }}
    }

    data = list(coll.aggregate([
        {"$match" : match},
        {"$group" : group}
    ]))
    
    # jmeno otce
    for otec in data:
        otec["jmeno"] = get_name(coll, druh, ZOO, otec["_id"])
        for pot in otec["potomci"]:
            # pridej jmeno matky
            pot["matka"] = get_name(coll, druh, ZOO, pot["matka"])
            # transformuj data
            pot["narozen"] = transformuj_datum(pot["narozen"])
            pot["odchod"] = transformuj_datum(pot["odchod"])
    
    return data

def create_table_potomstva(coll, druh, ZOO):
    data = []
    otci = get_otce(coll, druh, ZOO)
        
    for otec in otci:
        data.append([otec["jmeno"]])
        data.append([])
        
        # hlavicka
        row = ['cislo', 'pohlavi', 'rok', 'mesic', 'dny'] 
        row += [x for x in otec["potomci"][0].keys() if x not in row if x != 'vek']
        data.append(row)
        
        for pot in otec["potomci"]:
            row = [pot.pop('cislo'), pot.pop('pohlavi')]
            vek = pot.pop('vek')
            row += vek.values()
            for val in pot.values():
                row.append(val)
                
            data.append(row)
            
        # 2 blank rows
        data.append([])
        data.append([])

    return data


def create_all_tables(out_opt, data, data_book):
    all_data = []
    # extract common setting
    xlsx_file = out_opt['dir'] + 'tables/zpracovane_vse.xlsx'
    table_setting = [
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["stav k začátku roku.samec", "stav k začátku roku.samice", "stav k začátku roku.stav k začátku roku"],
                'coll' : data,
            },
            'sheet_name' : 'druhy_stav_zacatek',
            'caption' : "Druhy lemurů chovaných k 1.1. daného roku v českých zoologických zahradách v letech 1973-2017",
            'tex_file' : 'druhy_stav_zacatek.tex',
        },
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["odchov.samec", "odchov.samice", "odchov.nezname"],
                'coll' : data,
            },
            'sheet_name' : 'druhy_odchov',
            'caption' : "Odchov mláďat lemurů v českých zoologických zahradách v letech 1973-2017",
            'tex_file' : 'druhy_odchov.tex',
        },
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["živě narozená mláďata.samec", "živě narozená mláďata.samice", "živě narozená mláďata.nezname"],
                'coll' : data,
            },
            'sheet_name' : 'druhy_zive_narozena',
            'caption' : "Živě narozená mláďata lemurů v českých zoologických zahradách v letech 1973-2017",
            'tex_file' : 'druhy_zive_narozena.tex',
        },
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["živě narozená mláďata.samec", "živě narozená mláďata.samice", "živě narozená mláďata.nezname"],
                'coll' : data,
            },
            'sheet_name' : 'druhy_mrtve_narozena',
            'caption' : "Mrtvě narozená mláďata lemurů v českých zoologických zahradách v letech 1973-2017",
            'tex_file' : 'druhy_mrtve_narozena.tex',
        },
        {
            'data_func' : create_table_potomstva,
            'kwargs' : {
                'coll' : data_book,
                'druh' : "Lemur kata",
                'ZOO' : "Dvůr Králové",
            },
            'sheet_name' : 'lemur_kata_potomstvo',
            'caption' : "Otci, Lemur kata, Dvůr Králové",
            'tex_file' : 'lemur_kata_potomstvo.tex',
        },
    ]

    # go through all setting
    print("Prochazim celkem %i tabulek:" % len(table_setting))
    for i, setting in enumerate(table_setting):
        print("\tTabulka %i: %s" % (i+1, setting["caption"]))
        data = setting['data_func'](**setting['kwargs'])
        all_data.append({
            "sheet_name" : setting['sheet_name'],
            "data" : data,
            "header" : setting["caption"],
        })

    # ave all
    xls.save_xlsx(xlsx_file, all_data)
    print("Ulozeno do %s" % xlsx_file)
