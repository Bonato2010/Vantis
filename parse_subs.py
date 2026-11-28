import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
subs_dir = BASE_DIR / "workspace" / "subs"
input_file = subs_dir / "8TpjD8D9tIo.pt.json3"
output_file = subs_dir / "clean_transcript.json"

if not input_file.exists():
    print(f"[parse_subs] Arquivo de legenda não encontrado: {input_file}")
    exit(0)

with open(input_file, encoding='utf-8') as f:
    data = json.load(f)

parsed_segments = []
current_text = []
current_start = None
current_end = None

for ev in data.get('events', []):
    if 'segs' not in ev:
        continue
    t_start = ev.get('tStartMs', 0) / 1000.0
    d_dur = ev.get('dDurationMs', 0) / 1000.0
    t_end = t_start + d_dur
    
    seg_text = "".join([s.get('utf8', '') for s in ev['segs']]).strip()
    if not seg_text or seg_text == '\n':
        continue
        
    parsed_segments.append({
        'start': round(t_start, 2),
        'end': round(t_end, 2),
        'text': seg_text
    })

print(f"Total segmentos limpos: {len(parsed_segments)}")
for s in parsed_segments[50:60]:
    print(f"[{s['start']}s - {s['end']}s]: {s['text']}")

# Salvar formato simplificado
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(parsed_segments, f, ensure_ascii=False, indent=2)
