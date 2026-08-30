import json
from pathlib import Path
p=Path('reports'); p.mkdir(exist_ok=True)
files=sorted([x.name for x in p.glob('*.html') if x.name!='index.html'],reverse=True)
(p/'index.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
