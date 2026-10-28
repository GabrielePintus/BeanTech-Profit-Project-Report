"""Observed readiness margins against the selected Gamma rounded to calendar days."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def render(data, output):
    frame=pd.read_csv(data)
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#BAC7D8','pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.3,3.5),layout='constrained')
    edges=np.r_[frame.lower_day.to_numpy()-.5, frame.upper_day.iloc[-1]+.5]
    centers=(frame.lower_day+frame.upper_day)/2
    ax.bar(centers,frame.observed_pct,width=2.7,color='#AABBD2',edgecolor='white',lw=.4,label='Dati osservati')
    ax.stairs(frame.model_pct,edges,color='#245CC5',lw=1.8,label='Modello Gamma arrotondato')
    ax.set_xlim(0,82); ax.set_ylim(bottom=0)
    ax.set_xlabel('Margine [giorni]');ax.set_ylabel('Posizioni [%]')
    ax.grid(axis='y',color='#E5EAF1',lw=.6);ax.set_axisbelow(True)
    fig.legend(*ax.get_legend_handles_labels(),loc='outside lower center',frameon=True,edgecolor='#DCE3ED',facecolor='white',fontsize=9,ncol=2)
    fig.savefig(output,bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=root/'tables/data/readiness-generation-histogram.csv')
    p.add_argument('--output',type=Path,default=root/'figures/readiness-generation-distribution.pdf')
    a=p.parse_args();render(a.data,a.output)
