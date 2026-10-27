"""Plot the selected two-ODP allocation distribution and validation observations."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

def render(data,output):
    band=pd.read_csv(data/'odp-split-band.csv')
    val=pd.read_csv(data/'odp-split-validation.csv')
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#BAC7D8','pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.3,3.9),layout='constrained')
    x=band.quantity_kg/1000
    ax.fill_between(x,100*band.low,100*band.high,color='#DCE7F9',label='Intervallo centrale al 90% del modello')
    ax.plot(x,100*band['mean'],color='#245CC5',lw=1.4,label='Media del modello')
    ax.scatter(val.quantita_odv_kg/1000,100*val.first_share,s=20,facecolor='#B57C14',edgecolor='white',linewidth=.35,alpha=.85,zorder=3,label='59 posizioni di validazione')
    ax.axvline(93,color='#687888',lw=.9,ls='--',zorder=1)
    ax.text(95,96,'93 t',color='#56677A',fontsize=9,va='top')
    ax.set(xlabel='Quantità richiesta dalla posizione ODV [t]',ylabel='Quota del primo ODP [%]',ylim=(0,100))
    ax.grid(axis='y',color='#E5EAF1',lw=.6);ax.set_axisbelow(True)
    fig.legend(*ax.get_legend_handles_labels(),loc='outside lower center',
               frameon=True,facecolor='white',edgecolor='#DCE3ED',framealpha=1,
               fontsize=9,ncol=1,borderpad=.7)
    fig.savefig(output/'odp-quantity-split.pdf',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',type=Path,default=root/'figures/data');p.add_argument('--output-dir',type=Path,default=root/'figures');a=p.parse_args();render(a.data_dir,a.output_dir)
