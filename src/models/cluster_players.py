import pickle
import numpy as np
from matplotlib import pyplot as plt
from tqdm.notebook import tqdm
from boonnano import NanoHandle

with open('stats.pkl', 'rb') as f:
    data = pickle.load(f)

players = data['usernames']
skills = [feature[:-len("_level")] for feature in data['features'][4::3]]

levels = data['stats'][:, 4::3]
levels[np.where(levels == -1)] = 1

num_rows = len(levels)
hyperparams = {
    'all': {
        'pv': 0.127,
        'weight': 7*[16*23] + 16*[7*23],
        'feature_count': 23
    },
    'cb': {
        'pv': 0.060,
        'weight': 1,
        'feature_count': 7
    },
    'noncb': {
        'pv': 0.144,
        'weight': 1,
        'feature_count': 16
    }
}

results = {
    'all': {
        'id': np.zeros(num_rows, dtype='int'),
        'ri': np.zeros(num_rows)
    },
    'cb': {
        'id': np.zeros(num_rows, dtype='int'),
        'ri': np.zeros(num_rows)
    },
    'noncb': {
        'id': np.zeros(num_rows, dtype='int'),
        'ri': np.zeros(num_rows)
    }
}

nano = NanoHandle(timeout=None)
        
success, response = nano.open_nano('0')
if not success:
    raise ValueError(response)

batch_size = 10000

for experiment, params in hyperparams.items():
    success, response = nano.configure_nano(feature_count=params['feature_count'],
                                            min_val=1, max_val=99,
                                            weight=params['weight'],
                                            percent_variation=params['pv'])
    if experiment == 'all':
        dataset = levels
    elif experiment == 'cb':
        dataset = levels[:, :7]
    elif experiment == 'noncb':
        dataset = levels[:, 7:]

    with tqdm(total=num_rows) as progress_bar: 

        done = False
        batch_start = 0
        while not done:
            batch_end = batch_start + batch_size
            if batch_end >= num_rows:
                batch_end == num_rows
                done = True

            batch = dataset[batch_start:batch_end]
            success, response = nano.load_data(batch)
            if not success:
                raise ValueError(response)

            success, response = nano.run_nano(results='ID,RI')
            if not success:
                raise ValueError(response)
                
            results[experiment]['id'][batch_start:batch_end] = response['ID']
            results[experiment]['ri'][batch_start:batch_end] = response['RI']

            progress_bar.update(batch_end - batch_start)
            batch_start = batch_end

with open('clusters.pkl', 'wb') as f:
    pickle.dump(
        {
            'all': results['all']['id'],
            'cb': results['cb']['id'],
            'noncb': results['noncb']['id'],
        }, f)
