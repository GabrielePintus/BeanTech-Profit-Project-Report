"""Render report figures from aggregated evidence, without fitting or editing data.

Usage: python scripts/plot_statistical_mass.py
Requires numpy and matplotlib. Inputs contain pre-imputation histograms,
thresholds from the pipeline audit and exact quantiles for treated/untreated OdP.
"""
from pathlib import Path
import argparse,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
BLUE='#245CC5';GOLD='#E6AD16';TEAL='#008577';MUTED='#56677A'

def read(path):
 with path.open(newline='') as f:return list(csv.DictReader(f))
def logit(x):return np.log(x/(1-x))
def format_count(x,_):return f'{x:,.0f}'.replace(',','\u2009')

def render(data_dir,output_dir):
 output_dir.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#BAC7D8','axes.labelcolor':'#25313C','xtick.color':MUTED,'ytick.color':MUTED,'text.color':'#25313C','pdf.fonttype':42})
 hist=read(data_dir/'statistical-mass-histograms.csv');thresholds=read(data_dir/'statistical-mass-thresholds.csv')
 settings=[('Resa globale','a) Resa globale','Resa globale [%], scala logit'),('TRENOLUNA',r'b) Scarto relativo di $\mathtt{TRENOLUNA}$','Scarto / ingresso [%], scala logit'),('BANCHI',r'c) Scarto relativo dei $\mathtt{BANCHI}$','Scarto / ingresso [%], scala logit')]
 fig,axes=plt.subplots(3,1,figsize=(6.2,6.5),layout='constrained')
 for ax,(scope,title,xlabel) in zip(axes,settings):
  rows=[r for r in hist if r['scope']==scope]
  left=np.array([float(r['left']) for r in rows]);width=np.array([float(r['right'])-float(r['left']) for r in rows]);ordinary=np.array([int(r['count_other']) for r in rows]);flagged=np.array([int(r['count_candidate']) for r in rows])
  t=next(r for r in thresholds if r['scope']==scope and r['method']=='MAD')
  for bound,low,high in [('lower_pct','lower_ci_low_pct','lower_ci_high_pct'),('upper_pct','upper_ci_low_pct','upper_ci_high_pct')]:
   point=logit(float(t[bound])/100);lo=logit(float(t[low])/100);hi=logit(float(t[high])/100)
   ax.axvspan(lo,hi,color=GOLD,alpha=.19,zorder=0)
   ax.axvline(point,color=TEAL,lw=1.05,ls='--',zorder=3)
  ax.bar(left,ordinary,width=width,align='edge',color=BLUE,alpha=.78,edgecolor='white',linewidth=.25)
  ax.bar(left,flagged,width=width,bottom=ordinary,align='edge',color=GOLD,edgecolor='white',linewidth=.25)
  endpoints=[logit(float(t[k])/100) for k in ['lower_ci_low_pct','lower_ci_high_pct','upper_ci_low_pct','upper_ci_high_pct']]
  ax.set_xlim(min(left.min(),min(endpoints))-.08,max((left+width).max(),max(endpoints))+.08)
  perc=np.array([.01,.05,.1,.2,.5,1,2,5,10,20,40,60,80,90,95,98,99,99.5,99.9]);ticks=logit(perc/100)
  choose=(ticks>=ax.get_xlim()[0])&(ticks<=ax.get_xlim()[1]);px=perc[choose];tx=ticks[choose]
  # Keep labels comfortably separated on the transformed axis.
  keep=[]
  for j,x in enumerate(tx):
   if not keep or x-tx[keep[-1]]>.65:keep.append(j)
  ax.set_xticks(tx[keep],[f'{x:g}' for x in px[keep]])
  ax.set_ylabel('Frequenza');ax.set_xlabel(xlabel);ax.yaxis.set_major_formatter(FuncFormatter(format_count));ax.grid(axis='y',color='#E5EAF1',lw=.5);ax.set_axisbelow(True)
  n=int(ordinary.sum()+flagged.sum());c=int(flagged.sum())
  ax.set_title(title,loc='left',fontweight='bold',pad=8)
  ax.text(.01,.96,f'n = {n:,} · segnalati = {c}'.replace(',','\u2009'),transform=ax.transAxes,va='top',fontsize=8,color=MUTED,bbox=dict(facecolor='white',alpha=.85,edgecolor='none',pad=2))
 handles=[Patch(facecolor=BLUE,alpha=.78,label='Non segnalati'),Patch(facecolor=GOLD,label='MAD + IC95'),Line2D([0],[0],color=TEAL,lw=1.05,ls='--',label='Soglie MAD'),Patch(facecolor=GOLD,alpha=.19,label='IC95 delle soglie')]
 fig.legend(handles=handles,loc='outside upper center',ncol=4,frameon=False,fontsize=8,columnspacing=1.1)
 fig.savefig(output_dir/'statistical-mass-distributions.pdf',bbox_inches='tight');plt.close(fig)
 comparison=read(data_dir/'statistical-mass-comparison.csv')
 fig,axes=plt.subplots(2,1,figsize=(5.6,3.6),layout='constrained')
 groups=[('before','Prima · 101 ODP',BLUE),('after','Dopo · 101 ODP','#B5830A'),('untreated','Non trattati · 4 759 ODP',MUTED)]
 for ax,metric,title,limits,ticks in [
  (axes[0],'yield','a) Resa globale',(44,100),[50,60,70,80,90,100]),
  (axes[1],'root_scrap',r'b) Scarto relativo di $\mathtt{TRENOLUNA}$',(-2,56),[0,10,20,30,40,50])]:
  for y,(group,label,color) in zip([2,1,0],groups):
   row=next(r for r in comparison if r['group']==group and r['metric']==metric)
   stats={'whislo':float(row['p05_pct']),'q1':float(row['p25_pct']),
          'med':float(row['median_pct']),'q3':float(row['p75_pct']),
          'whishi':float(row['p95_pct'])}
   ax.bxp([stats],positions=[y],widths=.36,orientation='horizontal',
          showfliers=False,patch_artist=True,manage_ticks=False,
          boxprops=dict(facecolor=color+'35',edgecolor=color,linewidth=1),
          whiskerprops=dict(color=color,linewidth=1),
          capprops=dict(color=color,linewidth=1),
          medianprops=dict(color=color,linewidth=1.6),zorder=3)
  ax.set_yticks([2,1,0],[g[1] for g in groups]);ax.tick_params(axis='y',length=0,pad=8)
  ax.set_xlim(*limits);ax.set_ylim(-.5,2.55);ax.set_xticks(ticks)
  ax.set_title(title,loc='left',fontweight='bold',pad=8);ax.set_xlabel('[%]',labelpad=2)
  ax.grid(axis='x',color='#E5EAF1',lw=.6);ax.set_axisbelow(True);ax.spines['left'].set_visible(False)
 fig.savefig(output_dir/'statistical-mass-imputation.pdf',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
 root=Path(__file__).resolve().parents[1]
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,default=root/'figures/data');parser.add_argument('--output-dir',type=Path,default=root/'figures');args=parser.parse_args();render(args.data_dir,args.output_dir)
