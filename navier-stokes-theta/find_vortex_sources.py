"""Read-only, bounded search of the two named concept-paper families."""
import json
import re
from pathlib import Path
from pypdf import PdfReader

root=Path('D:/shovelcat-colony/companion/library')
found=[]
for name, relevant in (
    ('Unified_Waveguide_Civilian_Applications.pdf', (5,8,17)),
    ('MD-DEDS_Concept_Paper_v5.pdf', (3,)),
):
    reader=PdfReader(root/name)
    for index,page in enumerate(reader.pages):
        if index+1 not in relevant:
            continue
        text=page.extract_text() or ''
        if re.search(r'vortex|vortices|purif|helic|spiral|cyclon',text,re.I):
            row=dict(file=str(root/name),page=index+1,text=text)
            found.append(row)
            print(name,'page',index+1,flush=True)
            for line in text.splitlines():
                if re.search(r'vortex|vortices|purif|helic|spiral|cyclon',line,re.I):
                    print(line[:250],flush=True)
Path(__file__).with_name('vortex_source_passages.json').write_text(json.dumps(found,indent=2)+'\n',encoding='utf-8')
