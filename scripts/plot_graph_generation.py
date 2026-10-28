"""Compare macro-phase presence in observed and sampled validation cycles."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def render(data,output):
    frame=pd.read_csv(data/'graph-generation-phases.csv').set_index('phase')
    phases=['ANTIMIX','BANCHI','HPT','TAG','RADDR','TRATT_LFC','CONF','TRATT_LUNA','CIRCO']
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#BAC7D8','pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.3,4.2),layout='constrained')
    y=np.arange(len(phases));f=frame.loc[phases]
    ax.barh(y-.18,f.observed_pct,height=.32,color='#ADBBD0',label='Dati di validazione')
    ax.barh(y+.18,f.sampled_pct,height=.32,color='#245CC5',label='Cicli generati')
    ax.set_yticks(y,phases,fontfamily='monospace',fontsize=10)
    ax.invert_yaxis();ax.set_xlim(0,60)
    ax.set_xlabel('ODP in cui compare la macrofase [%]')
    ax.tick_params(axis='y',length=0,pad=5);ax.grid(axis='x',color='#E5EAF1',lw=.6);ax.set_axisbelow(True)
    fig.legend(*ax.get_legend_handles_labels(),loc='outside lower center',frameon=True,edgecolor='#DCE3ED',facecolor='white',fontsize=9,ncol=2)
    fig.savefig(output/'graph-generation-phases.pdf',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',type=Path,default=root/'figures/data');p.add_argument('--output-dir',type=Path,default=root/'figures');a=p.parse_args();render(a.data_dir,a.output_dir)
