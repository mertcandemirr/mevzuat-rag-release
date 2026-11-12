"""General terminology expansion only; no law/article IDs, gold data, or answers."""
import re
TERMS=[(r'\bdepozito\b','güvence'),(r'\bev\s+sahib(?:i|im|inin)\b','kiraya veren'),(r'\bfazla\s+mesai\b','fazla çalışma'),(r'\bevi\s+erken\s+boşalt\w*','kiralananın sözleşmenin bitiminden önce geri verilmesi'),(r'\bihbar\s+süresi\b','bildirim süreleri')]
def expand(question):
 normalized=question.casefold().replace('\u0307','');terms=[term for pattern,term in TERMS if re.search(pattern,normalized)]
 return question+(' '+ ' '.join(terms) if terms else ''),terms
