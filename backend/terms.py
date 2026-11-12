import re

def tokens(s):
    return re.findall(r'[0-9a-zçğıöşüâîû]+',s.replace('I','ı').replace('İ','i').lower())

def refs(q):
    aliases={'kvkk':'6698','tbk':'6098','iş kanunu':'4857','hmk':'6100','cmk':'5271','iik':'2004'}
    pairs=re.findall(r'\b(\d{3,4})\s*(?:sayılı.{0,60}?(?:madde|m\.)\s*|/|m\.?\s*)(\d{1,4})\b',q,re.I)
    for a,l in aliases.items():
        m=re.search(re.escape(a)+r'\s+(?:m(?:adde)?\.?\s*)?(\d{1,4})',q,re.I)
        if m:pairs.append((l,m[1]))
    return list(dict.fromkeys(pairs))

def exact_refs(text):
    q=text.casefold().replace('\u0307','');aliases={'kvkk':'6698','tbk':'6098','hmk':'6100','cmk':'5271','iik':'2004','i̇i̇k':'2004'}
    pairs=refs(text)
    for m in re.finditer(r'\b(\d{3,4})\s+sayılı\s+([^.;?!]{0,90}?)(?:madde|m\.)\s*(\d+)',q):
        for alias,law in aliases.items():
            if re.search(r'\b'+re.escape(alias)+r'\b',m[2]) and law!=m[1]:return [],'conflicting_law_reference'
    pairs+=re.findall(r'\b(\d{3,4})\s+(?:madde|m\.)\s*(\d+)\b',q)
    for alias,law in aliases.items():
        m=re.search(r'\b'+re.escape(alias)+r"(?:['’](?:nın|nin|nun|nün|ın|in|un|ün))?\s*(?:madde\s*|m\.\s*)?(\d+)\b",q)
        if m:pairs.append((law,m[1]))
    return list(dict.fromkeys(pairs)),None

