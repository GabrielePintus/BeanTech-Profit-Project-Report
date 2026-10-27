"""Plot section 4.4 from the verified zero-duration distribution summaries."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def render(data, output):
    with (data/'zero-duration-distributions.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':9,
        'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,
        'axes.edgecolor':'#BAC7D8','xtick.color':'#56677A','pdf.fonttype':42})
    fig, ax = plt.subplots(figsize=(6.2,2.8),layout='constrained')
    colors = {'positive_reference':('#D9E1EC','#56677A'), 'imputed':('#F6D78C','#A87508')}
    for y,phase in zip([2,1,0],['ANTIMIX','CONF','MOL']):
        for offset,group in [(.17,'positive_reference'),(-.17,'imputed')]:
            r=next(r for r in rows if r['phase']==phase and r['group']==group)
            face,edge=colors[group]
            stats=dict(whislo=float(r['p05']),q1=float(r['p25']),med=float(r['median']),q3=float(r['p75']),whishi=float(r['p95']))
            ax.bxp([stats],positions=[y+offset],widths=.22,orientation='horizontal',showfliers=False,manage_ticks=False,patch_artist=True,
                boxprops={'facecolor':face,'edgecolor':edge},whiskerprops={'color':edge},capprops={'color':edge},medianprops={'color':edge,'linewidth':1.7})
    ax.set_yticks([2,1,0],[r'$\mathtt{ANTIMIX}$',r'$\mathtt{CONF}$',r'$\mathtt{MOL}$'])
    ax.tick_params(axis='y',length=0,pad=8)
    ax.set_xscale('log');ax.set_xlim(1,400);ax.set_xticks([1,3,10,30,100,300],['1','3','10','30','100','300']);ax.minorticks_off()
    ax.set_ylim(-.55,2.55);ax.set_xlabel('Durata totale [min], scala logaritmica')
    ax.grid(axis='x',color='#E5EAF1',linewidth=.6);ax.set_axisbelow(True)
    fig.legend(handles=[Patch(facecolor=colors[k][0],edgecolor=colors[k][1],label=v) for k,v in [('positive_reference','Già positive'),('imputed','Imputate')]],loc='outside upper center',ncol=2,frameon=False,fontsize=8)
    fig.savefig(output/'zero-duration-distributions.pdf',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=root/'figures/data')
    parser.add_argument('--output-dir',type=Path,default=root/'figures')
    args=parser.parse_args();render(args.data_dir,args.output_dir)
