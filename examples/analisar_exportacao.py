"""Exemplo opcional. Instale pandas e matplotlib antes de executar.
python examples/analisar_exportacao.py smartwaste-dados.json
"""
import argparse,json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('arquivo');a=p.parse_args()
payload=json.loads(Path(a.arquivo).read_text(encoding='utf-8'))
df=pd.DataFrame(payload['events'])
if df.empty: raise SystemExit('A exportação ainda não contém eventos.')
df['emitted_at']=pd.to_datetime(df['emitted_at'],errors='coerce',utc=True)
df['fill_pct']=pd.to_numeric(df['fill_pct'],errors='coerce')
print('Tipos e estrutura:');df.info()
print('Ausentes por coluna:');print(df.isnull().sum())
print('IDs repetidos:',df.duplicated(subset=['event_id']).sum())
# Separar execuções evita misturar cenários independentes.
summary=df.groupby(['run_id','bin_id'],as_index=False)['fill_pct'].mean()
print(summary)
summary.to_csv('ocupacao_media.csv',index=False)
latest_run=df.iloc[0]['run_id']
summary[summary['run_id']==latest_run].set_index('bin_id')['fill_pct'].plot.bar(figsize=(12,4),color='#167655')
plt.ylabel('Ocupação média (%)');plt.title('Dados sintéticos: média das leituras exportadas');plt.tight_layout();plt.savefig('ocupacao_media.png',dpi=160)
