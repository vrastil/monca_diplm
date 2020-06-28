from __future__ import print_function

import os
import numpy as np
import unidecode

from IPython.display import display
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

FIRST_YEAR = 1973
LAST_YEAR = 2019

DEFAULT_PLOT_OPT = {
    'figsize': (14, 10),
    'no_suptitle': True,
    'suptitle_size': 30,
    'suptitle_y': 0.94,
}

def get_default_settings(plot_opt):
    if plot_opt is None:
            plot_opt = {}
    for key in DEFAULT_PLOT_OPT:
        if key not in plot_opt:
            plot_opt[key] = DEFAULT_PLOT_OPT[key]
    return plot_opt

def save_tex(filename, tex_opt):
    # creat tex string
    tex_fig = ("\\begin{figure}[ht]\n"
               "\t\\centering\n"
               "\t\\caption{%s}\n" % tex_opt['caption'])
    tex_fig += "\t\\includegraphics[width=1.0\\textwidth]{%s}\n" % filename
    tex_fig += "\t\\label{fig:%s}\n" % tex_opt['label']
    tex_fig += "\\end{figure}\n\n\n"
    
    # save to main file
    tex_file = tex_opt['tex_file']
    tex_file = unidecode.unidecode(tex_file)
    with open(tex_file, 'a+') as a_file:
        a_file.write(tex_fig)

    # save also to appendix
    tex_file = tex_file.replace('/main/', '/appendix/')
    tex_fig = tex_fig.replace('label{fig:', 'label{fig:app_')
    with open(tex_file, 'a+') as a_file:
        a_file.write(tex_fig)

def plot_basic(data, suptitle, out_opt, bar=False, plot_opt=None, tex_opt=None):
    # default setting
    plot_opt = get_default_settings(plot_opt)

    fig = plt.figure(figsize=plot_opt['figsize'])
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
    if not plot_opt['no_suptitle']:
        fig.suptitle(suptitle, size=plot_opt['suptitle_size'], y=plot_opt['suptitle_y'])

    if out_opt.get('show', True):
        plt.show()

    if out_opt.get('save', True):
        filename = out_opt['dir'] + 'plots/' + out_opt['filename']
        filename = unidecode.unidecode(filename)
        print(f'\tSaving {filename}')
        fig.savefig(filename, format="png")

    plt.close(fig=fig)

    
    # save info to tex file
    if tex_opt is not None:
        filename = '../data/plots/' + out_opt['filename']
        filename = unidecode.unidecode(filename)
        save_tex(filename, tex_opt)

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

def plot_one_zoo_rok(db, out_opt, druh=None, zoo=None, cats=None, legends=None, filename='', suptitle='', **kwargs):
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

    # rename categories
    if legends is not None and len(cats) == len(legends):
        for cat, legend in zip(cats, legends):
            my_data[legend] = my_data.pop(cat)

    # plot
    out_opt['filename'] = filename + '.png'
    if 'bar' in kwargs and kwargs['bar']:
        out_opt['filename'] = out_opt['filename'].replace('.png', '_' + ''.join([x[0] for x in cats]) + '_bar.png')
    plot_basic(my_data, suptitle, out_opt=out_opt, **kwargs)

def plot_one_zoo_rok_multiple(db, out_opt, druh_mlt=False, zoo_mlt=False, filename='', suptitle='', **kwargs):
    druhy = db.distinct('Druh', {}) if druh_mlt else [None]
    zoos = db.distinct('ZOO', {}) if zoo_mlt else [None]
    if 'tex_opt' in kwargs:
        label = kwargs['tex_opt']['label']
        caption = kwargs['tex_opt']['caption']
        tex = True
    else:
        tex = False
    
    for druh in druhy:
        for zoo in zoos:
            suptitle_ = suptitle
            filename_ = filename
            if zoo is not None:
                suptitle_ = suptitle_.replace('#ZOO#', zoo)
                filename_ = filename_.replace('#ZOO#', zoo.replace(' ', '_'))
                if tex:
                    kwargs['tex_opt']['label'] = label.replace('#ZOO#', zoo.replace(' ', '_'))
                    kwargs['tex_opt']['caption'] = caption.replace('#ZOO#', zoo)
            if druh is not None:
                suptitle_ = suptitle_.replace('#DRUH#', druh)
                filename_ = filename_.replace('#DRUH#', druh.replace(' ', '_'))
                if tex:
                    kwargs['tex_opt']['label'] = label.replace('#DRUH#', druh.replace(' ', '_'))
                    kwargs['tex_opt']['caption'] = caption.replace('#DRUH#', druh)
            plot_one_zoo_rok(db, out_opt, druh=druh, zoo=zoo, filename=filename_, suptitle=suptitle_, **kwargs)
    

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

def init_tex(out_opt, setting):
    if 'tex_opt' in setting['kwargs']:
        # prepare filename
        if 'tex_file' not in setting['kwargs']['tex_opt']:
            tex_file = out_opt['dir'] + 'plots/main/' + setting['kwargs']['filename'] + '.tex'
            setting['kwargs']['tex_opt']['tex_file'] = tex_file
        else:
            tex_file = setting['kwargs']['tex_opt']['tex_file']
        setting['kwargs']['tex_opt']['label'] = setting['kwargs']['filename']

        # delete old files
        if os.path.exists(tex_file):
            os.remove(tex_file)
            os.remove(tex_file.replace('/main/', '/appendix/'))


def create_all_plots(coll, out_opt):
    plots_settings = [
        {
            'name': 'Porodnost za vsechny ZOO a vsechny druhy',
            'plot_func': plot_one_zoo_rok,
            'kwargs': {
                'druh': None,
                'zoo': None,
                'cats': ['stav k začátku roku.samice', 'živě narozená mláďata'],
                'legends': ['počet samic' ,'živě narozená mláďata'],
                'filename': 'porodnost_vse',
                'suptitle': 'Porodnost mláďať v ČR v letech %i - %i' % (FIRST_YEAR, LAST_YEAR),
                'tex_opt': {
                    'caption': 'Porodnost mláďať v ČR v letech %i - %i' % (FIRST_YEAR, LAST_YEAR),
                }
            },
        },
        {
            'name': 'Porodnost za vsechny ZOO, jednotlive druhy',
            'plot_func': plot_one_zoo_rok_multiple,
            'kwargs': {
                'druh_mlt': True,
                'cats': ['stav k začátku roku.samice', 'živě narozená mláďata'],
                'legends': ['počet samic' ,'živě narozená mláďata'],
                'filename': 'porodnost_#DRUH#',
                'suptitle': 'Porodnost mláďať druhu #DRUH#\nv ČR v letech %i - %i' % (FIRST_YEAR, LAST_YEAR),
                'plot_opt' : {'suptitle_y' : 0.99},
                'tex_opt': {
                    'caption': 'Porodnost mláďať druhu #DRUH# v ČR v letech %i - %i' % (FIRST_YEAR, LAST_YEAR),
                    'tex_file':  out_opt['dir'] + 'plots/main/' + 'porodnost_druhy.tex',
                }
            },
        }
    ]

    print("Prochazim celkem %i grafu:" % len(plots_settings))
    for i, setting in enumerate(plots_settings):
        print("  Graf %i: %s" % (i+1, setting['name']))
        init_tex(out_opt, setting)
        setting['plot_func'](coll, out_opt, **setting['kwargs'])
    plt.close('all')
    