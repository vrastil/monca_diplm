from __future__ import print_function

import datetime

import xlsx_manipulation as xls

LAST_YEAR = 2018

def create_table(coll, cats, min_year=None, max_year=None):

    druhy = coll.distinct('Druh')
    roky = sorted(coll.distinct('Rok'))
    data = []

    if min_year is not None:
            roky = [x for x in roky if x >= min_year]
    if max_year is not None:
            roky = [x for x in roky if x <= max_year]
            
    # hlavicka
    data.append([''] + roky)
    
    # jednotlive druhy
    for druh in druhy:
        row = [druh]
        # get all data
        match = [{cat : {"$gt" : 0}} for cat in cats]
        match = {"Druh" : druh, "$or" : match}
        if min_year is not None:
            match["Rok"] = {"$gte" : min_year}
        if max_year is not None:
            if "Rok" in match:
                match["Rok"]["$lte"] = max_year
            else:
                match["Rok"] = {"$lte" : max_year}
        group = {cat.replace('.', '@') : {"$sum" : "$" + cat} for cat in cats}
        group["_id"] = "$Rok"
        group["Pocet ZOO"] = {"$sum" : 1}
        my_data = list(coll.aggregate([
                {"$match"  : match},
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

def get_mul_lines(key):
    # special character for dot
    key = key.replace('@', '.')

    # special character for newline
    if '\\' in key:
        return key[:key.find('\\')-1], key[key.find('\\')+2:]
    else:
        return key, None

def create_table_history(coll):
    # keys
    key_zacatek = "Začátek chovu \\ (rok)"
    key_zacatek_zoo = "Začátek chovu \\ (ZOO)"
    key_pocet_jed = "Počet jedinců \\ (k 31@12@%i)" % LAST_YEAR
    key_pocet_zoo = "Chováno v ZOO \\ (k 31@12@%i)" % LAST_YEAR

    # zacatek chovu dle druhu
    historie_lemuru = list(coll.aggregate([{"$group" : {
        "_id" : "$Druh",
        key_zacatek : {"$min" : "$Rok"},
        "Celkem odchováno \\ jedinců" : {"$sum" : {"$sum" : ["$odchov.samec", "$odchov.samice", "$odchov.neznámé"]}},
        "Celkem narozeno \\ jedinců" : {"$sum" : {"$sum" : [
            "$živě narozená mláďata.samec", "$živě narozená mláďata.samice", "$živě narozená mláďata.neznámé"]}},
        }}, {"$sort" : {key_zacatek : 1}}
    ]))

    # pridej ZOO
    for doc in historie_lemuru:
        doc[key_zacatek_zoo] = ','.join([doc["ZOO"] for doc in coll.find(
            {"Druh" : doc["_id"], "Rok" : doc[key_zacatek]},
            {"ZOO" : 1}
        )])
        
    # pridej posledni rok: pocet ZOO, pocet lemuru
    for doc in historie_lemuru:
        rec = coll.aggregate([
            {"$match" : {"Druh" : doc["_id"], "Rok" : LAST_YEAR}},
            {"$group" : {
                "_id" : {},
                key_pocet_jed : {"$sum" : {"$sum" : [
                    "$stav ke konci roku.samec", "$stav ke konci roku.samice", "$stav ke konci roku.neznámé"]}},
                key_pocet_zoo : {"$sum" : 1},
            }}])

        try:
            rec = next(rec)
        except StopIteration:
            rec = {key_pocet_jed : 0, key_pocet_zoo : 0}
        
        doc[key_pocet_jed] = rec[key_pocet_jed]
        doc[key_pocet_zoo] = rec[key_pocet_zoo]

    # hlavicka
    keys = [x for x in historie_lemuru[0].keys() if x != '_id']
    # !!! manual sortinf of keys
    keys[1], keys[3] = keys[3], keys[1]
    data = [[''], ['']]
    for key in keys:
        h1, h2 = get_mul_lines(key)
        data[0].append(h1)
        data[1].append(h2)

    # pridej zaznamy
    for rec in historie_lemuru:
        row = [rec['_id']] + [rec[key] for key in keys]
        data.append(row)

    return data

def save_tex(tex_file, data, caption, num_h_rows=1):
    with open(tex_file, 'w') as a_file:
        # get length
        length = len(data[0]) - 1

        # write header
        a_file.write(u"\\begin{table}\n")
        a_file.write(u"\\begin{tabular}{l" + 'c'*length + "}\n")
        a_file.write(u"\t\\hline\n")
        for i in range(num_h_rows):
            row = [str(x) for x in data[i]]
            row = u"\t" + u" & ".join(row) + " \\\\\n"
            a_file.write(row)
        a_file.write(u"\t\\hline\n")

        # write data
        for row in data[num_h_rows:]:
            row = [str(x) for x in row]
            row = u"\t" + u" & ".join(row) + " \\\\\n"
            a_file.write(row)

        # write footer
        a_file.write("\t\\hline\n")
        a_file.write("\\end{tabular}\n")
        a_file.write(u"\\caption{%s}\n" % caption)
        a_file.write("\\end{table}\n")

def create_one_table(all_data, i, data_func, kwargs, caption, sheet_name, tex_file, num_h_rows):
        print("\tTabulka %i: %s" % (i+1, caption))
        data = data_func(**kwargs)
        # save data for xlsx
        all_data.append({
            "sheet_name" : sheet_name,
            "data" : data,
            "header" : caption,
        })
        # save .tex file
        save_tex(tex_file, data, caption, num_h_rows)

def create_all_tables(out_opt, data, data_book):
    table_setting = [
                {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["stav k začátku roku.samec", "stav k začátku roku.samice", "stav k začátku roku.stav k začátku roku"],
                'coll' : data,
            },
            'duplicate' : {
                'min_year' : [1973, 1991, 2001, 2010],
                'max_year' : [1990, 2000, 2009, LAST_YEAR],
            },
            'sheet_name' : 'druhy_stav_zacatek',
            'caption' : "Druhy lemurů chovaných k 1.1. daného roku v českých zoologických zahradách v letech MIN_YEAR---MAX_YEAR",
            'tex_file' : 'druhy_stav_zacatek_MIN_YEAR_MAX_YEAR.tex',
        },
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["odchov.samec", "odchov.samice", "odchov.nezname"],
                'coll' : data,
            },
            'duplicate' : {
                'min_year' : [1973, 1991, 2001, 2010],
                'max_year' : [1990, 2000, 2009, LAST_YEAR],
            },
            'sheet_name' : 'druhy_odchov',
            'caption' : "Odchov mláďat lemurů v českých zoologických zahradách v letech MIN_YEAR---MAX_YEAR",
            'tex_file' : 'druhy_odchov_MIN_YEAR_MAX_YEAR.tex',
        },
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["živě narozená mláďata.samec", "živě narozená mláďata.samice", "živě narozená mláďata.nezname"],
                'coll' : data,
            },
            'duplicate' : {
                'min_year' : [1973, 1991, 2001, 2010],
                'max_year' : [1990, 2000, 2009, LAST_YEAR],
            },
            'sheet_name' : 'druhy_zive_narozena',
            'caption' : "Živě narozená mláďata lemurů v českých zoologických zahradách v letech MIN_YEAR---MAX_YEAR",
            'tex_file' : 'druhy_zive_narozena_MIN_YEAR_MAX_YEAR.tex',
        },
        {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["mrtvě narozená mláďata.samec", "mrtvě narozená mláďata.samice", "mrtvě narozená mláďata.nezname"],
                'coll' : data,
            },
            'duplicate' : {
                'min_year' : [1973, 1991, 2001, 2010],
                'max_year' : [1990, 2000, 2009, LAST_YEAR],
            },
            'sheet_name' : 'druhy_mrtve_narozena',
            'caption' : "Mrtvě narozená mláďata lemurů v českých zoologických zahradách v letech MIN_YEAR---MAX_YEAR",
            'tex_file' : 'druhy_mrtve_narozena_MIN_YEAR_MAX_YEAR.tex',
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
        {
            'data_func' : create_table_history,
            'kwargs' : {
                'coll' : data,
            },
            'sheet_name' : 'historie_chovu',
            'caption' : "Historie chovu lemurů v ČR v letech 1973-%i" % LAST_YEAR,
            'tex_file' : 'historie_chovu.tex',
            'num_h_rows' : 2
        },
    ]

    # go through all setting
    all_data = []
    print("Prochazim celkem %i tabulek:" % len(table_setting))
    for i, setting in enumerate(table_setting):
        # extract setting
        caption = setting["caption"]
        kwargs = setting['kwargs']
        sheet_name = setting['sheet_name']
        num_h_rows = setting.get('num_h_rows', 1)
        tex_file = out_opt['dir'] + 'tables/' + setting['tex_file']
        data_func = setting['data_func']

        if "duplicate" in setting:
            for min_year, max_year in zip(setting["duplicate"]["min_year"], setting["duplicate"]["max_year"]):
                caption = setting["caption"]
                caption = caption.replace("MIN_YEAR", str(min_year))
                caption = caption.replace("MAX_YEAR", str(max_year))
                sheet_name = setting['sheet_name']
                sheet_name = sheet_name.replace("MIN_YEAR", str(min_year))
                sheet_name = sheet_name.replace("MAX_YEAR", str(max_year))
                tex_file = out_opt['dir'] + 'tables/' + setting['tex_file']
                tex_file = tex_file.replace("MIN_YEAR", str(min_year))
                tex_file = tex_file.replace("MAX_YEAR", str(max_year))
                kwargs["min_year"] = min_year
                kwargs["max_year"] = max_year
                create_one_table(all_data, i, data_func, kwargs, caption, sheet_name, tex_file, num_h_rows)   
        else:
            create_one_table(all_data, i, data_func, kwargs, caption, sheet_name, tex_file, num_h_rows)

    # save all
    xlsx_file = out_opt['dir'] + 'tables/zpracovane_vse.xlsx'
    xls.save_xlsx(xlsx_file, all_data)
    print("Ulozeno do %s" % xlsx_file)
