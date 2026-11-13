import json, sys, numpy as np
T = json.load(open(f'{sys.argv[1]}_tasks.json'))
for k in sys.argv[2:]:
    t = T[k]; p = t['train'][0]; a, b = np.array(p['input']), np.array(p['output'])
    print(f"== {k}  train pairs {len(t['train'])}, shape {a.shape}")
    for r in range(a.shape[0]):
        print(''.join('.' if x == 0 else str(x) for x in a[r]), '  ', ''.join(('.' if y == 0 else str(y)) if x == y else ('*' if False else str(y)) for x, y in zip(a[r], b[r])),
              '  ', ''.join(' ' if x == y else '^' for x, y in zip(a[r], b[r])))
