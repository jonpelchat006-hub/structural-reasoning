"""Insert recorded sample data in the literal inline visualization fragment."""
from pathlib import Path
import json
import math

source=Path(__file__).with_name('return_paths_results.json')
result=json.loads(source.read_text())[-1]
points=[]
for row in result['sample_paths']:
    if 1.5<=row['t']<=5.4:
        x,y,z=row['positions'][2][0]
        points.append([round(row['t'],3),round(math.hypot(x-math.pi,y-math.pi),5),round(z,5)])
target=Path('C:/Users/GamerTech/.codex/visualizations/2026/09/09/01a087a7-d698-7dc0-b7e4-5f16a62beb6e/returning-flow.html')
markup=target.read_text(encoding='utf-8')
assert '__RETURN_DATA__' in markup
target.write_text(markup.replace('__RETURN_DATA__',json.dumps(points)),encoding='utf-8')
print(len(points),'samples',result['n'],result['dt'])
