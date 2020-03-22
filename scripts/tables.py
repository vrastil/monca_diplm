from __future__ import print_function
import unidecode
import datetime
from dateutil.relativedelta import relativedelta

import xlsx_manipulation as xls

LAST_YEAR = 2018

TRANSLATE = {
    'Lemur kata': 'Lemur catta',
    'Lemur běločelý': 'Eulemur albifrons',
    'Vari červený': 'Varecia rubra',
    'Lemur mongoz': 'Eulemur mongoz',
    'Lemur korunkatý': 'Eulemur coronatus',
    'Lemur Sclaterův': 'Eulemur flavifrons',
    'Lemur červenobřichý': 'Eulemur rubriventer',
    'Lemur tmavý': 'Eulemur macaco',
    'Lemur vari': 'Varecia variegata',
}

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
    doc = coll.find_one({"Druh" : druh, "ZOO" : ZOO, "číslo" : cislo})
    if doc:
        return doc["jméno"]
    else:
        return "UNK (%s)" % str(cislo)

def get_val_from_keys(a_dict, keys):
    for key in keys:
        if key in a_dict:
            return a_dict[key], key
    else:
        return None, None

def get_time_of_death(pot):
    pozn, key = get_val_from_keys(pot, ['Poznámka', 'poznámka'])
    if pozn == "Úhyn":
        pot[key] = ""
        datum, _ = get_val_from_keys(pot, ["Narození", "narozen"])
        narozen = transformuj_datum(datum, form_in='out', form_out=False)
        vek = relativedelta(days=pot['věk']['dny'], months=pot['věk']['měsíce'], years=pot['věk']['roky'])
        return transformuj_datum(vek+narozen)
    else:
        return ""

def transformuj_datum(datum, form_in=None, form_out=None):
    if form_in is None:
        form_in = '%m/%d/%Y'
    elif form_in == 'out':
        form_in = '%d.%m.%Y'

    if form_out is None:
        form_out = '%d.%m.%Y'

    # prazdne stringy netransformuj
    if datum:
        # dostan datetime
        if isinstance(datum, str) and form_in:
            datum = datetime.datetime.strptime(datum, form_in)

        # preved zas na string
        if form_out:
            datum = datum.strftime(form_out)
    # 0 preved na prazdny string
    else:
        datum = ''

    return datum


def is_odchovany(pot):
    vek, _ = get_val_from_keys(pot, keys=['vek', 'věk'])
    vek = relativedelta(days=vek['dny'], months=vek['měsíce'], years=vek['roky'])
    limit = relativedelta(years=0, month=6, day=0)
    base_date = datetime.datetime(year=1950, month=1, day=1) # arbitrary

    return (base_date + vek) > (base_date + limit)

def get_num_pot(potomci):
    # narozeny
    male = [x for x in potomci if x['Sex'] == 'M']
    female = [x for x in potomci if x['Sex'] == 'F']
    unknown = [x for x in potomci if x not in male if x not in female]
    pocet = "%i.%i.%i" % (len(male), len(female), len(unknown))

    # odchovany
    male = [x for x in male if is_odchovany(x)]
    female = [x for x in female if is_odchovany(x)]
    unknown = [x for x in unknown if is_odchovany(x)]
    odchovano = "%i.%i.%i" % (len(male), len(female), len(unknown))

    # return
    return pocet, odchovano


def get_otce(coll, druh, ZOO):
    match = {'ZOO' : ZOO, 'Druh' : druh, 'Rodiče.Samec' : {"$gt" : 0}}
    group = {
        "_id" : "$Rodiče.Samec",
        "pocet_potomku" : {"$sum" : 1},
        "potomci" : {"$push" : {
            "Číslo" : "$číslo",
            "Jméno" : "$jméno",
            "věk" : "$věk",
            "Matka" : "$Rodiče.Samice",
            "Sex" : "$pohlaví",
            "Narození" : "$narozen",
            "Odchod" : "$odchod",
            "Poznámka" : "$poznámka"
        }}
    }

    data = list(coll.aggregate([
        {"$match" : match},
        {"$group" : group}
    ]))
    
    # jmeno otce
    for otec in data:
        otec["Jméno"] = get_name(coll, druh, ZOO, otec["_id"])
        
        for pot in otec["potomci"]:
            # pridej jmeno matky
            pot["Matka"] = get_name(coll, druh, ZOO, pot["Matka"])
            # transformuj data
            pot["Narození"] = transformuj_datum(pot["Narození"])
            pot["Odchod"] = transformuj_datum(pot["Odchod"])
            # pridej uhyn
            pot["Úhyn"] = get_time_of_death(pot)

        # additional info for other tables
        doc = coll.find_one({"Druh" : druh, "ZOO" : ZOO, "číslo" : otec["_id"]})
        otec["Číslo"] = otec["_id"]
        if doc:
            otec["Narození"] = transformuj_datum(doc["narozen"])
            otec["místo narození"] = " " + doc["místo narození"]
            otec["Úhyn"] = get_time_of_death(doc)
            otec["Odchod"] = transformuj_datum(doc["odchod"])
        else:
            otec["Narození"] = otec["Úhyn"] = otec["Odchod"] = otec["místo narození"] = ""
        otec["Počet mláďat"], otec["Odchováno"] = get_num_pot(otec["potomci"])
    
    return data

def get_matky(coll, druh, ZOO):
    match = {'ZOO' : ZOO, 'Druh' : druh, 'Rodiče.Samice' : {"$gt" : 0}}
    group = {
        "_id" : "$Rodiče.Samice",
        "pocet_potomku" : {"$sum" : 1},
        "potomci" : {"$push" : {
            "Číslo" : "$číslo",
            "Jméno" : "$jméno",
            "věk" : "$věk",
            "Otec" : "$Rodiče.Samec",
            "Sex" : "$pohlaví",
            "Narození" : "$narozen",
            "Odchod" : "$odchod",
            "Poznámka" : "$poznámka"
        }}
    }

    data = list(coll.aggregate([
        {"$match" : match},
        {"$group" : group}
    ]))
    
    # jmeno matky
    for matka in data:
        matka["Jméno"] = get_name(coll, druh, ZOO, matka["_id"])
        for pot in matka["potomci"]:
            # pridej jmeno otce
            pot["Otec"] = get_name(coll, druh, ZOO, pot["Otec"])
            # transformuj data
            pot["Narození"] = transformuj_datum(pot["Narození"])
            pot["Odchod"] = transformuj_datum(pot["Odchod"])
            # pridej uhyn
            pot["Úhyn"] = get_time_of_death(pot)

        # additional info for other tables
        doc = coll.find_one({"Druh" : druh, "ZOO" : ZOO, "číslo" : matka["_id"]})
        matka["Číslo"] = matka["_id"]
        if doc:
            matka["Narození"] = transformuj_datum(doc["narozen"])
            matka["místo narození"] = " " + doc["místo narození"]
            matka["Úhyn"] = get_time_of_death(doc)
            matka["Odchod"] = transformuj_datum(doc["odchod"])
        else:
            matka["Narození"] = matka["Úhyn"] = matka["Odchod"] = matka["místo narození"] = ""


        matka["Počet mláďat"], matka["Odchováno"] = get_num_pot(matka["potomci"])
    
    return data

def create_table_potomstva(coll, druh, ZOO, all_data=None):
    if all_data is None:
        all_data = []

    # get otce, save otce
    otci = get_otce(coll, druh, ZOO)
    for otec in otci:
        data = []
        
        # hlavicka
        header = ['Číslo', 'Sex', 'Narození', 'Matka', 'Úhyn', 'Odchod', 'Poznámka'] 
        data.append(header)
        
        for pot in otec["potomci"]:
            row = [pot[x] for x in header]
            data.append(row)
        all_data.append({
            "rodic" : otec["Jméno"],
            "druh" : druh,
            "ZOO" : ZOO,
            "data" : data,
            "caption" : "Potomci samce druhu %s (\\textit{%s}) jménem %s v ZOO %s k 31.12.%i" % (
                druh, TRANSLATE[druh], otec["Jméno"], ZOO, LAST_YEAR)
        })
        
    # get matky, save matky
    matky = get_matky(coll, druh, ZOO)
    for matka in matky:
        data = []
        
        # hlavicka
        header = ['Číslo', 'Sex', 'Narození', 'Otec', 'Úhyn', 'Odchod', 'Poznámka'] 
        data.append(header)
        
        for pot in matka["potomci"]:
            row = [pot[x] for x in header]
            data.append(row)
        all_data.append({
            "rodic" : matka["Jméno"],
            "druh" : druh,
            "ZOO" : ZOO,
            "data" : data,
            "caption" : "Potomci samice druhu %s (\\textit{%s}) jménem %s v ZOO %s k 31.12.%i" % (
                druh, TRANSLATE[druh], matka["Jméno"], ZOO, LAST_YEAR)
        })
    return all_data

def create_table_potomstva_summary(coll, druh, ZOO, all_data=None):
    if all_data is None:
        all_data = []
        
    # hlavicka
    header = ['Číslo', 'Jméno', 'Narození', 'Úhyn', 'Odchod', 'Počet mláďat', 'Odchováno']
    first_y = LAST_YEAR

    # get otce, save otce
    data = [header]
    otci = sorted(get_otce(coll, druh, ZOO), key=lambda x: x['Číslo'])
    for otec in otci:
        narozen = transformuj_datum(otec['Narození'], form_in='out', form_out=False)
        if narozen:
            first_y = min(first_y, narozen.year)
        otec["Narození"] += otec["místo narození"]
        row = [otec[x] for x in header]
        data.append(row)
    
    # do not save empty data
    if len(data) > 1:
        all_data.append({
            "rodic" : "samec %s %s" % (druh, ZOO),
            "druh" : druh,
            "ZOO" : ZOO,
            "data" : data,
            "caption" : "Chovní samci druhu %s (\\textit{%s}) v ZOO %s v letech %i---%i" % (
                druh, TRANSLATE[druh], ZOO, first_y, LAST_YEAR)
        })
        
    # hlavicka
    header = ['Číslo', 'Jméno', 'Narození', 'Úhyn', 'Odchod', 'Počet mláďat', 'Odchováno']
    first_y = LAST_YEAR

    # get matky, save matky
    data = [header]
    matky = sorted(get_matky(coll, druh, ZOO), key=lambda x: x['Číslo'])
    for matka in matky:
        narozen = transformuj_datum(matka['Narození'], form_in='out', form_out=False)
        if narozen:
            first_y = min(first_y, narozen.year)
        matka["Narození"] += matka["místo narození"]
        row = [matka[x] for x in header]
        data.append(row)
    
    # do not save empty data
    if len(data) > 1:
        all_data.append({
            "rodic" : "samice %s %s" % (druh, ZOO),
            "druh" : druh,
            "ZOO" : ZOO,
            "data" : data,
            "caption" : "Chovné samice druhu %s (\\textit{%s}) v ZOO %s v letech %i---%i" % (
                druh, TRANSLATE[druh], ZOO, first_y, LAST_YEAR)
        })
        
    return all_data

def create_table_potomstva_all(coll):
    all_data = []
    for ZOO in coll.distinct('ZOO', {}):
        for druh in coll.distinct('Druh', {}):
            create_table_potomstva(coll, druh, ZOO, all_data=all_data)
    return all_data

def create_table_potomstva_summary_all(coll):
    all_data = []
    for ZOO in coll.distinct('ZOO', {}):
        for druh in coll.distinct('Druh', {}):
            create_table_potomstva_summary(coll, druh, ZOO, all_data=all_data)
    return all_data

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

def save_tex(tex_file, data, caption, num_h_rows=1, adjustwidth=-0.5):
    with open(tex_file, 'w') as a_file:
        # get length
        length = len(data[0]) - 1

        # write header
        a_file.write(u"\\begin{table}[htb]\n")
        a_file.write(u"\\begin{adjustwidth}{%.1fcm}{}\n" % adjustwidth)
        a_file.write(u"\\caption{%s}\n" % caption)
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
        a_file.write("\\end{adjustwidth}\n")
        a_file.write("\\end{table}\n")

def tex_potomstvo(tex_file, all_data, caption, num_h_rows=1, adjustwidth=-2.5):
    with open(tex_file, 'w') as a_file:
        zoo = last_zoo = None
        for val in all_data:
            zoo = val['ZOO']
            # clear page for every ZOO
            if last_zoo is None:
                a_file.write(u"\\subsection{%s}\n" % zoo)
            elif zoo != last_zoo:
                a_file.write(u"\\clearpage% Flush page\n")
                a_file.write(u"\\subsection{%s}\n" % zoo)

            last_zoo = zoo

            rodic = val["rodic"]
            data = val["data"]
            caption_otec = val["caption"]
            file_otec = tex_file.replace(".tex", "_%s.tex" % rodic.replace(" ", "_"))
            file_otec = unidecode.unidecode(file_otec)
            save_tex(file_otec, data, caption_otec, num_h_rows, adjustwidth=-2.5)
            a_file.write(u"\\input{../data/tables/%s}\n" % file_otec.split('/')[-1])

def xls_potomstvo(all_data):
    xls_data = []
    for val in all_data:
        rodic = val["rodic"]
        data = val["data"]
        xls_data.append([rodic])
        xls_data += data
        
        # 2 blank rows
        xls_data += [[], []]

    return xls_data

def get_birth_by_druh_month(coll):
    match = {"narozen": {"$type": 9}}
    project = {
                "month": {"$month": "$narozen"},
                "Druh" : "$Druh",
                "ZOO" : "$ZOO"
                
            }

    group = {x : {"$sum" : {"$cond": [{"$eq": ['$Druh', x]}, 1, 0]}} for x in coll.distinct("Druh")}
    group["_id"] = "$month"
    group["Celkem"] = {"$sum" : 1}

    cursor = coll.aggregate([
        {"$match" : match},
        {"$project": project},
        { "$group" :group}
    ])

    return list(cursor)

def get_birth_by_druh(coll):
    match = {"narozen": {"$type": 9}}
    project = {
                "month": {"$month": "$narozen"},
                "Druh" : "$Druh",
                "ZOO" : "$ZOO"
                
            }

    group = {x : {"$sum" : {"$cond": [{"$eq": ['$Druh', x]}, 1, 0]}} for x in coll.distinct("Druh")}
    group["_id"] = "$month"
    group["Celkem"] = {"$sum" : 1}
    group2 = {x : {"$sum" : "$%s" % x} for x in coll.distinct("Druh")}
    group2["_id"] = None
    group2["Celkem"] = {"$sum" : "$Celkem"}
    cursor = coll.aggregate([
        {"$match" : match},
        {"$project": project},
        {"$group" :group},
        {"$group": group2}
    ])

    data = list(cursor)[0]
    data.pop('_id')
    return data

def create_table_narozeni_abs(coll):
    # hlavicka
    months = list(range(1, 13)) 
    data_all = [[''] + months]

    # data
    data = get_birth_by_druh_month(coll)
    keys = [x for x in data[0] if x != '_id']

    # prochazej po lemurech
    for key in keys:
        row = [key]
        # pro jednotlive mesice
        for month in months:
            try:
                val = next((x[key] for x in data if x['_id'] == month))
            except StopIteration:
                val = 0
            row.append(val)
        data_all.append(row)

    return data_all

def create_table_narozeni_rel(coll):
    data_all = create_table_narozeni_abs(coll)
    data_celkem = get_birth_by_druh(coll)
    # hlavicku nech
    for row in data_all[1:]:
        key = row[0]
        for i, val in enumerate(row[1:]):
            row[i+1] = "%.1f" % (val*100.0/data_celkem[key])
    return data_all

def create_one_table(all_data, i, data_func, kwargs, caption, sheet_name, tex_file, num_h_rows, tex_func=save_tex, xls_func=None, adjustwidth=-0.5):
        print("  Tabulka %i: %s" % (i+1, caption))
        # get data
        data = data_func(**kwargs)
        data_xls = xls_func(data) if xls_func is not None else data

        # save data for xlsx
        all_data.append({
            "sheet_name" : sheet_name,
            "data" : data_xls,
            "header" : caption,
        })
        # save .tex file
        tex_func(tex_file, data, caption, num_h_rows, adjustwidth)

def create_all_tables(out_opt, coll_roc, coll_knihy):
    table_setting = [
                {
            'data_func' : create_table,
            'kwargs' : {
                'cats' : ["stav k začátku roku.samec", "stav k začátku roku.samice", "stav k začátku roku.stav k začátku roku"],
                'coll' : coll_roc,
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
                'coll' : coll_roc,
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
                'coll' : coll_roc,
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
                'coll' : coll_roc,
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
            'data_func' : create_table_potomstva_all,
            'kwargs' : {
                'coll' : coll_knihy,

            },
            'tex_func' : tex_potomstvo,
            'xls_func' : xls_potomstvo,
            'sheet_name' : 'potomstvo',
            'caption' : "Potomci lemuru (vsechny druhy, vsechny ZOO)",
            'tex_file' : 'potomstvo.tex',
        },
        {
            'data_func' : create_table_history,
            'kwargs' : {
                'coll' : coll_roc,
            },
            'sheet_name' : 'historie_chovu',
            'caption' : "Historie chovu lemurů v ČR v letech 1973-%i" % LAST_YEAR,
            'tex_file' : 'historie_chovu.tex',
            'num_h_rows' : 2
        },
        {
            'data_func' : create_table_narozeni_abs,
            'kwargs' : {
                'coll' : coll_knihy,
            },
            'sheet_name' : 'narozeni_mesice',
            'caption' : "Absolutní počty narození dle měsíce",
            'tex_file' : 'narozeni_mesice_abs.tex',
            'adjustwidth' : -2.5
        },
        {
            'data_func' : create_table_narozeni_rel,
            'kwargs' : {
                'coll' : coll_knihy,
            },
            'sheet_name' : 'narozeni_mesice',
            'caption' : "Relativní počty narození (v \\%) dle měsíce",
            'tex_file' : 'narozeni_mesice_rel.tex',
            'adjustwidth' : -2.5
        },
        {
            'data_func' : create_table_potomstva_summary_all,
            'kwargs' : {
                'coll' : coll_knihy,

            },
            'tex_func' : tex_potomstvo,
            'xls_func' : xls_potomstvo,
            'sheet_name' : 'potomstvo_souhrn',
            'caption' : "Potomci lemuru, souhrn (vsechny druhy, vsechny ZOO)",
            'tex_file' : 'potomstvo_souhrn.tex',
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
        tex_func = setting.get("tex_func", save_tex)
        adjustwidth = setting.get("adjustwidth", -0.5)
        xls_func = setting.get("xls_func", None)

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
                create_one_table(all_data, i, data_func, kwargs, caption, sheet_name, tex_file, num_h_rows, tex_func, xls_func, adjustwidth)
        else:
            create_one_table(all_data, i, data_func, kwargs, caption, sheet_name, tex_file, num_h_rows, tex_func, xls_func, adjustwidth)

    # save all
    xlsx_file = out_opt['dir'] + 'tables/zpracovane_vse.xlsx'
    xls.save_xlsx(xlsx_file, all_data)
    print("Ulozeno do %s" % xlsx_file)
