"""Conditional duration intervals for the report's generated material-flow example."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


def render(data, output):
    frame = pd.read_csv(data)
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['DejaVu Serif'], 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False, 'axes.edgecolor': '#BAC7D8', 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(6.3, 2.8), layout='constrained')
    # Transparent figure and axes preserve the report's shared yellow example background.
    fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    y = np.arange(len(frame))
    ax.hlines(y, frame.lower95_minutes, frame.upper95_minutes, color='#8AA9E8', lw=4, zorder=2)
    ax.vlines(frame.lower95_minutes, y-.09, y+.09, color='#245CC5', lw=1)
    ax.vlines(frame.upper95_minutes, y-.09, y+.09, color='#245CC5', lw=1)
    ax.scatter(frame.predicted_minutes, y, marker='o', color='#245CC5', s=38, zorder=3)
    ax.scatter(frame.sampled_minutes, y, marker='D', color='#B38118', edgecolor='white', linewidth=.5, s=34, zorder=4)
    ax.set_yticks(y, frame.phase, fontfamily='monospace', fontsize=10)
    ax.set_ylim(2.5, -.5); ax.set_xscale('log'); ax.set_xlim(4, 2200)
    ticks=[5, 15, 60, 240, 960]
    ax.set_xticks(ticks, [str(x) for x in ticks]); ax.minorticks_off()
    ax.set_xlabel('Durata [minuti]'); ax.tick_params(axis='y', length=0, pad=7)
    ax.grid(axis='x', color='#DCE2EB', lw=.6); ax.set_axisbelow(True)
    handles=[Line2D([], [], color='#8AA9E8', lw=4, label='Intervallo al 95%'), Line2D([], [], marker='o', linestyle='none', color='#245CC5', label='Media'), Line2D([], [], marker='D', linestyle='none', color='#B38118', label='Estrazione')]
    fig.legend(handles=handles, loc='outside lower center', ncol=3, frameon=False, fontsize=9, handlelength=1.2, columnspacing=1.5)
    fig.savefig(output, bbox_inches='tight', transparent=True); plt.close(fig)

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=root/'tables/data/duration-generation-example.csv')
    parser.add_argument('--output', type=Path, default=root/'figures/duration-generation-example.pdf')
    args=parser.parse_args(); render(args.data, args.output)
