"""Phase presence when the whole selected cascade receives requested quantity only."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def render(data,output):
    f=pd.read_csv(data).set_index('phase')
    phases=['ANTIMIX','BANCHI','HPT','TAG','RADDR','TRATT_LFC','CONF','TRATT_LUNA','CIRCO','MOL']
    f=f.loc[phases];y=np.arange(len(f))
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#BAC7D8','pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.3,4.3),layout='constrained')
    ax.barh(y-.18,f.observed_pct,height=.32,color='#ADBBD0',label='Dati osservati')
    ax.barh(y+.18,f.quantity_only_pct,height=.32,color='#245CC5',label='Generazione dalla sola quantità')
    ax.set_yticks(y,phases,fontfamily='monospace',fontsize=10);ax.invert_yaxis();ax.set_xlim(0,70)
    ax.set_xlabel('ODP in cui compare la macrofase [%]')
    ax.tick_params(axis='y',length=0,pad=5);ax.grid(axis='x',color='#E5EAF1',lw=.6);ax.set_axisbelow(True)
    fig.legend(*ax.get_legend_handles_labels(),loc='outside lower center',frameon=True,edgecolor='#DCE3ED',facecolor='white',fontsize=8.5,ncol=2)
    fig.savefig(output,bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=root/'tables/data/cascade-generation-phases.csv');p.add_argument('--output',type=Path,default=root/'figures/cascade-generation-phases.pdf');a=p.parse_args();render(a.data,a.output)
