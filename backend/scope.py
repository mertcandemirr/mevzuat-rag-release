"""Explicit law/article scope checks; no question-specific answer mappings."""
import re
from backend.terms import exact_refs

def scoped_references(question, available_laws):
    normalized=question.casefold().replace('\u0307','')
    if re.search(r'\b(?:geçici|ek)\s*(?:madde|m\.)?\s*\d+',normalized):
        return [],'non_normal_article_requires_temporal_review'
    pairs,error=exact_refs(question)
    if error:
        return pairs,error
    explicit=re.findall(r'\b(\d{1,5})\s+sayılı\b',normalized)
    if any(law not in available_laws for law in explicit):
        return [],'missing_explicit_law'
    # Turkish commonly places an ordinal article number before "maddesi".
    pattern=r'\b(\d{1,5})\s+sayılı\s+[^.;?!\n]{0,90}?\b(\d+)\s*\.\s*madd(?:e|esi|enin|esine|esini)\b'
    pairs+=re.findall(pattern,normalized)
    compound=[]
    for pattern in [r'\b(\d{3,5})\s+sayılı\s+[^.;?!\n]{0,90}?\b(\d+)\s*/\s*([a-zçğıöşü])\b',r'\b(\d{3,5})\s+(?:madde|m\.)\s*(\d+)\s*/\s*([a-zçğıöşü])\b']:
        compound.extend((law,number+'/'+letter.upper()) for law,number,letter in re.findall(pattern,normalized))
    for law,article in compound:
        number=article.split('/')[0]
        standalone=re.search(r'(?:madde|m\.)\s*'+re.escape(number)+r'\b(?!\s*/)',normalized)
        if not standalone:pairs=[p for p in pairs if p!=(law,number)]
    return list(dict.fromkeys(compound+pairs)),None
