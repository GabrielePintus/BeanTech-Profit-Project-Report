"""Plot section 4.3 from verified aggregate references and paired corrections."""
from pathlib import Path
import argparse, csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

BLUE='#245CC5'; GOLD='#B5830A'; MUTED='#56677A'
def rows(path):
    with path.open(newline='') as stream: return list(csv.DictReader(stream))
def render(data,output):
    reference={r['phase']:r for r in rows(data/'statistical-duration-reference.csv')}
    paired=rows(data/'statistical-duration-paired.csv')
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':9,
                         'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,
                         'axes.edgecolor':'#BAC7D8','axes.labelcolor':'#25313C',
                         'xtick.color':MUTED,'ytick.color':'#25313C','pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.2,3.2),layout='constrained')
    phases=['BANCHI','TRATT_LUNA','TRATT_LFC']
    for y,phase in zip([2,1,0],phases):
        r=reference[phase]
        stats={'whislo':float(r['p05']),'q1':float(r['p25']),'med':float(r['median']),
               'q3':float(r['p75']),'whishi':float(r['p95'])}
        ax.bxp([stats],positions=[y+.13],widths=.18,orientation='horizontal',showfliers=False,
               patch_artist=True,manage_ticks=False,boxprops={'facecolor':'#D9E1EC','edgecolor':MUTED},
               whiskerprops={'color':MUTED},capprops={'color':MUTED},medianprops={'color':MUTED,'linewidth':1.6})
        selected=sorted([r for r in paired if r['macro_fase']==phase],key=lambda r:float(r['before_minutes']))
        for offset,r in zip(np.linspace(-.035,.035,len(selected)) if len(selected)>1 else [0],selected):
            before,after=float(r['before_minutes']),float(r['after_minutes'])
            ax.plot([before,after],[y-.16+offset,y-.16],color=BLUE,alpha=.18,lw=.7,zorder=2)
            ax.scatter([before],[y-.16+offset],marker='o',s=23,facecolors='white',edgecolors=BLUE,lw=1,zorder=3)
        after=float(selected[0]['after_minutes'])
        ax.scatter([after],[y-.16],marker='D',s=32,color=GOLD,zorder=4)
        label=f'{after:,.2f}'.replace(',', '\u2009')
        ax.annotate(label,(after,y-.16),xytext=(0,-14),textcoords='offset points',ha='center',color=GOLD,fontsize=8)
    labels=[r'$\mathtt{BANCHI}$ · 12',r'$\mathtt{TRATT\_LUNA}$ · 1',r'$\mathtt{TRATT\_LFC}$ · 1']
    ax.set_yticks([2,1,0],labels);ax.tick_params(axis='y',length=0,pad=8)
    ax.set_xscale('log');ax.set_xlim(1,12000);ax.set_xticks([1,10,100,1000,10000],['1','10','100','1 000','10 000'])
    ax.minorticks_off();ax.set_ylim(-.6,2.5);ax.set_xlabel('Durata totale [min], scala logaritmica')
    ax.grid(axis='x',color='#E5EAF1',lw=.6);ax.set_axisbelow(True)
    handles=[Patch(facecolor='#D9E1EC',edgecolor=MUTED,label='Riferimento non segnalato'),
             Line2D([],[],marker='o',markerfacecolor='white',markeredgecolor=BLUE,ls='',label='Prima'),
             Line2D([],[],marker='D',color=GOLD,ls='',label='Dopo')]
    fig.legend(handles=handles,loc='outside upper center',ncol=3,frameon=False,fontsize=8)
    fig.savefig(output/'statistical-duration-effects.pdf',bbox_inches='tight');plt.close(fig)
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',type=Path,default=root/'figures/data');p.add_argument('--output-dir',type=Path,default=root/'figures')
    args=p.parse_args();render(args.data_dir,args.output_dir)
