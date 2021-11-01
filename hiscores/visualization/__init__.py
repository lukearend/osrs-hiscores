import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.stats import pearsonr

from hiscores.data import exclude_missing


# Use default seaborn theme.
sns.set_theme()


#  Each annotation is some text with a line pointing the top of a bar.
def _annotate_level(ax, level, count, annotation, ymax):

    # Rescale y as a fraction of plot height to a y-value in plot's log-scale.
    y = np.exp(annotation['y_frac'] * np.log(ymax))
    ax.plot([level, annotation['x']], [count, y], color='#404040', linewidth=1)
    ax.text(annotation['x'], y, annotation['text'], fontsize=14, color='#404040',
            horizontalalignment='center', verticalalignment='bottom')


# Plot a histogram showing the number of players at each level
# between 1 and 99 for a skill, with annotations if provided.
def player_skills_histogram(levels_df, skill, out_file, annotations=None):

    fig, ax = plt.subplots(figsize=(16, 5))
    fig.tight_layout()

    ax.set_title('OSRS player {} levels'.format(skill), weight='bold', fontsize=16)
    ax.set_xlabel('{} level'.format(skill[0].upper() + skill[1:]), fontsize=14)
    ax.set_ylabel('Number of players', fontsize=14)

    data = exclude_missing(levels_df[skill])
    hist = sns.histplot(ax=ax, data=data, discrete=False if skill == 'total' else True)

    levels = [int(bar.xy[0] + 0.5) for bar in hist.patches]
    counts = [bar.get_height() for bar in hist.patches]
    max_count = np.max(counts)

    if skill == 'total':
        ax.set_xlim(650, 2277 + 50)
        ax.set_xticks(list(range(700, 2277, 100)) + [2277])
    else:
        ax.set_xlim(0, 100)
        ax.set_xticks([1] + list(range(5, 99, 5)) + [99])

    # Explicitly dial in the y-scale.
    ax.set_yscale('log')
    ymax = max_count * 10
    ax.set_ylim(1 - 0.1 * np.e, ymax)

    # Add annotations.
    if annotations:
        counts = {level: count for level, count in zip(levels, counts)}
        for level, annotation in annotations.items():
            _annotate_level(ax, level, counts[level], annotation, ymax)


    fig.savefig(out_file, bbox_inches='tight')
    plt.show()
    plt.close(fig)
