from __future__ import print_function

import numpy as np

from IPython.display import display
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

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
