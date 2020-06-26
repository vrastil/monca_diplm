from __future__ import print_function

import numpy as np

from IPython.display import display
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def plot_basic(data, suptitle, out_opt, bar=False):
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
    filename = out_opt['dir'] + 'plots/' + out_opt['filename']
    fig.savefig(filename, format="png")

def plot_all_zoo_rok(db, druh, cat, out_opt):
    query = {
        'Druh' : druh,
    }

    proj = {
        '_id' : 0,
        'Rok' : 1,
        'ZOO' : 1,
        cat : 1
    }

    my_data = {}

    for doc in db.find(query, proj):
        zoo = doc['ZOO']
        rok = doc['Rok']
        narozeny = sum(list(doc[cat].values()))
        
        if zoo not in my_data:
            my_data[zoo] = []
        my_data[zoo].append([rok, narozeny])

    # plot
    suptitle = druh + ' (' + cat + ')'
    out_opt['filename'] = druh.replace(' ', '_') + '_' + cat.replace(' ', '_') + '.png'
    plot_basic(my_data, suptitle, out_opt=out_opt)

def get_proj(proj, cat):
    if '.' in cat:
        cat = cat.split('.')[0]
    proj[cat] = 1

def get_val(doc, cat, val=0):
    # recursive cal
    if '.' in cat:
        key = cat.split('.')[0]
        cat = '.'.join(cat.split('.')[1:])
        val += get_val(doc[key], cat, val=val)
    else:
        if isinstance(doc[cat], dict):
            val += sum(list(doc[cat].values()))
        else:
            val += doc[cat]
    return val

def plot_one_zoo_rok(db, druh, zoo, cats, out_opt, **kwargs):
    query = {}
    if isinstance(druh, str):
        query['Druh'] = druh
    else:
        druh = ''
    if isinstance(zoo, str):
        query['ZOO'] = zoo
    else:
        zoo = ''

    proj = {
        '_id' : 0,
        'Rok' : 1,
    }
    for cat in cats:
        get_proj(proj, cat)

    my_data = {cat : [] for cat in cats}

    # first sum all years
    tmp = {cat : {} for cat in cats}

    for doc in db.find(query, proj):
        rok = doc['Rok']
        for cat in cats:
            pocet = get_val(doc, cat)
            pocet += tmp[cat].get(rok, 0)
            tmp[cat][rok] = pocet

    # then save to data for plot
    # TODO use shorthand
    for cat, data in tmp.items():
        for rok, pocet in data.items():
            my_data[cat].append([rok, pocet])

    # plot
    suptitle = druh + ', ' + zoo + ' (' + out_opt['suptitle'] + ')'
    out_opt['filename'] = druh.replace(' ', '_') + '_' + zoo.replace(' ', '_') + '_' + out_opt['suptitle'].replace(' ', '_') + '.png'
    if 'bar' in kwargs and kwargs['bar']:
        out_opt['filename'] = out_opt['filename'].replace('.png', '_' + ''.join([x[0] for x in cats]) + '_bar.png')
    plot_basic(my_data, suptitle, out_opt=out_opt, **kwargs)


def plot_cats_rok(db, druh, cats, out_opt):
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

    my_data = {cat : [] for cat in cats}

    all_doc = list(db.find(query, proj))
    roky = sorted(set([doc['Rok'] for doc in all_doc]))

    for cat in cats:
        my_data[cat] = [[rok, 0] for rok in roky]

    for doc in all_doc:
        rok = doc['Rok']
        for cat in cats:
            pocet = sum(list(doc[cat].values()))
            item = next(x for x in my_data[cat] if x[0] == rok)
            item[1] += pocet

    # plot
    suptitle = druh + ' (' + out_opt['suptitle'] + ')'
    out_opt['filename'] = druh.replace(' ', '_') + '_' + out_opt['suptitle'].replace(' ', '_') + '.png'
    plot_basic(my_data, suptitle, out_opt=out_opt)
