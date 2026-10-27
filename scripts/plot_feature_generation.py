"""Plot the selected VAEAC's per-feature gain over independent marginals."""
import argparse,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABELS={'classe_carbonio':'Classe di carbonio','codice_cliente':'Codice cliente','descrizione_tipo_lunghezza':'Tipo di lunghezza','descrizione_marca_acciaio':"Marca dell’acciaio",'finitura':'Finitura','forma':'Forma','descrizione_macrociclo':'Macrociclo','marca_cliente':'Marca cliente','codice_materiale':'Codice materiale','modello_pp_richiesto':'Modello PP richiesto','nfa':'NFA','stato_fisico':'Stato fisico','versione_tecnica':'Versione tecnica','tolleranza_massima_lunghezza':'Tolleranza massima lunghezza','tolleranza_minima_lunghezza':'Tolleranza minima lunghezza','difetto_superficiale_massimo':'Difetto superficiale massimo','sezione_grezza_pp':'Sezione grezza PP','indice_criticita':'Indice di criticità','lunghezza_richiesta':'Lunghezza richiesta','dimensione_1_mm':'Prima dimensione'}

def render(data,output):
    with (data/'feature-generation-scores.csv').open() as f: rows=sorted(csv.DictReader(f),key=lambda r:float(r['skill_nats']))
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#BAC7D8','pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.2,5.3),layout='constrained')
    y=range(len(rows));gain=[float(r['skill_nats']) for r in rows]
    ax.barh(y,gain,color='#D9E5F4',height=.65)
    ax.scatter(gain,y,color='#245CC5',s=15,zorder=3)
    ax.set_yticks(list(y),[LABELS[r['feature']] for r in rows],fontsize=10.5)
    ax.tick_params(axis='y',length=0,pad=6)
    ax.axvline(0,color='#56677A',lw=.7);ax.set_xlim(-.08,5)
    ax.set_xlabel('Riduzione del punteggio\nrispetto alle marginali [nat]',fontsize=10.5)
    ax.grid(axis='x',color='#E5EAF1',lw=.6);ax.set_axisbelow(True)
    fig.savefig(output/'feature-generation-gains.pdf',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=root/'figures/data');p.add_argument('--output-dir',type=Path,default=root/'figures')
    a=p.parse_args();render(a.data_dir,a.output_dir)
