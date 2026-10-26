"""Small prose spacing helper; preserve URLs and code exactly."""
import re

def normalize_prose(text):
    pieces=re.split(r'(```[\s\S]*?```|`[^`\n]*`|https?://[^\s)]+)',text)
    for i in range(0,len(pieces),2):
        s=pieces[i]
        s=re.sub(r'([А-ЯЁа-яё])([0-9A-Za-z])',r'\1 \2',s)
        s=re.sub(r'([0-9A-Za-z])([А-ЯЁа-яё])',r'\1 \2',s)
        s=re.sub(r'\b([A-Za-z]{3,})([0-9])',r'\1 \2',s)
        s=re.sub(r'\b(S[0-9]{2})(?=[A-Za-z])',r'\1 ',s)
        s=re.sub(r':(?=[^\s*])',': ',s)
        s=re.sub(r'(\*\*[^*\n]+):\s+\*\*',r'\1:**',s)
        s=re.sub(r';(?=\S)','; ',s)
        s=re.sub(r',(?=[А-ЯЁа-яёA-Za-z])',', ',s)
        pieces[i]=s
    return ''.join(pieces)
