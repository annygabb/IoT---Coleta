"""Seções de evidência medida para o relatório exportado."""
from datetime import datetime
from statistics import mean
from reportlab.platypus import PageBreak,KeepTogether
from reportlab.graphics.shapes import Drawing,Rect,String,Line
from reportlab.lib import colors
from .experiments import seconds

LOGIC={
 'SET_SPEED':'Muda o ritmo do relógio simulado. Mais velocidade pode gerar mais enchimento e deslocamento por segundo real; a cadência de telemetria permanece independente.',
 'SET_STRATEGY':'Muda a escolha das próximas rotas na fog. Distância e coleta dependem também da posição dos caminhões e da demanda; compare testes equivalentes para avaliar eficiência.',
 'WEATHER':'Altera as condições de trânsito do modelo. O tempo de viagem e as decisões de rota podem mudar; não representa previsão meteorológica real.',
 'BLOCK_ROAD':'Bloqueia ou libera a EPTG no grafo. Dijkstra recalcula caminhos disponíveis, podendo aumentar distâncias ou alterar a ordem de atendimento.',
 'PAUSE':'Pausa a evolução física da simulação. A comunicação e a sincronização da fila continuam funcionando.',
 'RESUME':'Retoma a evolução física. A coleta e os deslocamentos voltam a avançar conforme a velocidade configurada.',
 'FORCE_CRITICAL':'Eleva a ocupação da lixeira escolhida para provocar uma decisão da fog. Uma coleta rápida pode ocorrer antes da próxima amostra; o primeiro estado observado pode já refletir o atendimento.',
 'CLOUD_LINK':'Desabilitar o enlace suspende novos envios, preservando a fila SQLite. Ao habilitar, lotes voltam a ser enviados. Um lote iniciado antes da interrupção ainda pode concluir.',
 'CANARY_START':'Testa firmware virtual em cinco sensores e usa os demais como controle. Erros acima do limite levam à reversão após a janela de observação; a versão efetiva pode diferir da versão testada.'}

def add_evidence(story,payload,p,section,table):
 a=payload.get('state',{}).get('architecture',{});ev=payload.get('evidence',{});samples=ev.get('samples',[]);batches=ev.get('batches',[]);actions=ev.get('actions',[])
 remote=a.get('cloud_url','').startswith('https://glyvjheauocycvwieytr.supabase.co/')
 section('Edge, fog e nuvem - caminho dos dados')
 table([['Camada','Implementação e efeito'],['Edge','Sensores e caminhões virtuais; publica snapshots e recebe comandos por MQTT 3.1.1, QoS 1.'],['Fog','Broker local, decisões de rota e fila SQLite. Confirma snapshots após armazenamento; reenvia comandos até confirmação.'],['Nuvem','Supabase Free / São Paulo (sa-east-1). Configuração verificada em 19/10/2026. HTTPS para a função smartwaste-api.' if remote else 'Emulador local ou outro destino configurado. Este relatório não comprova hospedagem Supabase.'],['Condição atual',f"{a.get('cloud_status','-')} | última confirmação: {a.get('last_sync','-')} | telemetria histórica a cada {a.get('telemetry_every','-')} snapshots (~1 s por snapshot)."]],[100,670])
 d=Drawing(770,94)
 for x,title,detail in [(0,'EDGE','Medição e execução'),(270,'FOG','Decisão e fila em disco'),(540,'NUVEM','Histórico persistente')]:
  d.add(Rect(x,23,225,65,fillColor=colors.HexColor('#E0EDE5'),strokeColor=colors.HexColor('#167655')));d.add(String(x+12,65,title,fontName='SWBold',fontSize=12));d.add(String(x+12,43,detail,fontName='SWBody',fontSize=9))
 for x,label in [(225,'MQTT'),(495,'HTTPS' if remote else 'HTTP')]:
  d.add(Line(x+3,52,x+42,52));d.add(Line(x+35,57,x+42,52));d.add(Line(x+35,47,x+42,52));d.add(String(x+3,12,label,fontName='SWBody',fontSize=8))
 story.append(d)
 story.append(p('QoS 1 admite duplicações. IDs de evento evitam repetir o histórico na fog e na nuvem. A confirmação MQTT e a confirmação de aplicação têm funções diferentes: receber um pacote não comprova que o comando foi aplicado.'))
 story.append(PageBreak());section('Medições de MQTT e envio à nuvem')
 rows=[['Indicador','Edge','Fog']]
 for label,key in [('Publicações aceitas pelo cliente','tx_messages'),('Bytes de payload enviados','tx_payload_bytes'),('Mensagens válidas recebidas','rx_messages'),('Bytes de payload recebidos','rx_payload_bytes'),('Mensagens inválidas / descartadas','invalid_messages')]:rows.append([label,a.get('edge_mqtt',{}).get(key,'-'),a.get('fog_mqtt',{}).get(key,'-')])
 table(rows,[420,175,175]);story.append(p('Os bytes MQTT são somente payload, sem cabeçalhos ou tráfego TCP. Publicações aceitas pelo cliente não são contagem de PUBACK. A medição da edge chega no snapshot seguinte.'))
 durations=sorted(b['duration_ms'] for b in batches if b.get('duration_ms') is not None and not b.get('error'))
 def percentile(q):return round(durations[min(len(durations)-1,int((len(durations)-1)*q))],2) if durations else '-'
 table([['Nuvem nesta sessão da fog','Resultado'],['Tentativas / sucesso / falha',f"{a.get('cloud_attempts',0)} / {a.get('cloud_successes',0)} / {a.get('cloud_failures',0)}"],['Bytes JSON tentados (inclui reenvios)',a.get('cloud_payload_bytes',0)],['Confirmações de eventos / ainda pendentes',f"{a.get('synced',0)} / {a.get('pending_cloud',0)}"],['Lotes bem-sucedidos na janela retida',len(durations)],['Tempo do lote: mediana / P95 (ms)',f'{percentile(.5)} / {percentile(.95)}']],[420,350])
 story.append(p('Tempo do lote inclui a requisição completa e a resposta de confirmação, não é ping nem garantia de desempenho do provedor. Contadores de sessão reiniciam com a fog; a fila persiste. Limites do plano Free continuam aplicáveis. Sem teste controlado equivalente, não há comprovação numérica de ganho de latência ou economia em relação à arquitetura anterior.'))
 if len(samples)>1:
  story.append(PageBreak())
  section('Fila pendente ao longo do teste')
  start=samples[0]['at'];span=max(1,seconds(start,samples[-1]['at']));peak=max(1,max(s.get('pending',0) for s in samples));d=Drawing(770,175)
  d.add(Line(45,30,755,30));d.add(Line(45,30,45,153))
  for i in range(5):
   y=30+i*30;d.add(String(0,y,str(round(peak*i/4)),fontName='SWBody',fontSize=8));d.add(Line(45,y,755,y,strokeColor=colors.HexColor('#DCE7DF')))
  pts=[(45+seconds(start,s['at'])/span*710,30+s.get('pending',0)/peak*120) for s in samples]
  for first,last in zip(pts,pts[1:]):d.add(Line(*first,*last,strokeColor=colors.HexColor('#167655'),strokeWidth=1.5))
  d.add(String(45,10,'0 s',fontName='SWBody',fontSize=8));d.add(String(665,10,f'{span:.1f} s reais',fontName='SWBody',fontSize=8));story.append(d)
  story.append(p(f"Janela: {samples[0]['at']} até {samples[-1]['at']} (UTC). Eixo vertical: eventos pendentes. Pico: {peak}. A queda da fila junto a confirmações de lote mostra a recuperação; a subida pode ocorrer quando a geração supera o envio."))
 if batches:
  section('Últimos lotes - evidência do envio')
  table([['UTC','Eventos no lote / confirmados','JSON bytes','Tempo ms','HTTP / erro']]+[[b.get('at'),f"{b.get('requested')} / {b.get('acknowledged')}",b.get('payload_bytes'),b.get('duration_ms'),f"{b.get('http_status','-')} / {b.get('error') or 'sem erro'}"] for b in batches[-8:]],[230,170,100,100,170])
 story.append(PageBreak());section('Alterações e impacto observado')
 story.append(p('A linha do tempo registra somente ações feitas a partir desta atualização. Não reconstrói mudanças anteriores. Antes = estado conhecido ao enviar; observado = primeira amostra compatível após a confirmação; depois = nova amostra pelo menos 10 segundos reais mais tarde. A janela real consta em cada ação.'))
 if not actions:story.append(p('Nenhuma ação registrada. Faça uma alteração, aguarde a confirmação e pelo menos 10 segundos antes de exportar novamente.'))
 for index,item in enumerate(reversed(actions)):
  if index:story.append(PageBreak())
  names={'SET_SPEED':'Velocidade','SET_STRATEGY':'Estratégia de rota','WEATHER':'Clima','BLOCK_ROAD':'Bloqueio da EPTG','PAUSE':'Pausar','RESUME':'Retomar','CLOUD_LINK':'Conexão com a nuvem','CANARY_START':'Teste de versão','FORCE_CRITICAL':'Lixeira crítica'}
  statuses={'QUEUED':'aguardando confirmação','APPLIED':'confirmada','OBSERVED':'estado observado','REJECTED':'rejeitada'}
  section(names.get(item['action'],item['action'])+' | '+statuses.get(item.get('status'),'-'))
  before=item.get('before') or {};after=item.get('after') or {};follow=item.get('followup') or {}
  story.append(p(f"Solicitado em UTC: {item.get('at')} | parâmetros: {item.get('requested')} | via: {item.get('via')}\nConfirmação: {item.get('ack_status') or 'ainda não recebida'} | tempo até confirmação: {item.get('ack_ms','-')} ms. {item.get('error') or ''}"))
  story.append(p(LOGIC.get(item['action'],'Observe os valores confirmados na próxima telemetria.')))
  rows=[['Métrica','Antes','Primeiro estado observado','Após >= 10 s','Variação antes → última amostra']]
  fields=[('Fila pendente','pending'),('Recebidos na fog','received'),('Confirmados na nuvem','synced'),('Ocupação média %','mean_fill'),('Distância total km','distance_km'),('Coletado total kg','collected_kg')]
  extra={'SET_SPEED':[('Velocidade simulada','speed')],'SET_STRATEGY':[('Estratégia','strategy')],'WEATHER':[('Clima','weather')],'PAUSE':[('Pausa','paused')],'RESUME':[('Pausa','paused')],'BLOCK_ROAD':[('EPTG bloqueada','blocked')],'CLOUD_LINK':[('Enlace nuvem','cloud_enabled'),('Estado da nuvem','cloud_status')],'CANARY_START':[('Estado do canário','canary_status'),('Relatos no teste','canary_reports'),('Erros no teste','canary_errors')],'FORCE_CRITICAL':[('Lixeiras com >= 85%','critical_bins')]}
  for label,key in fields+extra.get(item['action'],[]):
   last=follow or after;v=last.get(key);old=before.get(key);delta=round(v-old,2) if isinstance(v,(int,float)) and not isinstance(v,bool) and isinstance(old,(int,float)) and not isinstance(old,bool) else '-'
   rows.append([label,old,after.get(key),follow.get(key),delta])
  def versions(sample):
   counts={}
   for version in sample.get('firmware',{}).values():counts[version]=counts.get(version,0)+1
   return ', '.join(f'{version}: {count} sensores' for version,count in sorted(counts.items())) or '-'
  if item['action']=='CANARY_START':rows.append(['Firmware em uso',versions(before),versions(after),versions(follow),'-'])
  table(rows,[185,140,165,140,140])
  if follow:story.append(p(f"Amostra posterior: {follow['at']} UTC | {seconds(after['at'],follow['at']):.2f} s após o primeiro estado observado."))
  elif after:story.append(p('Amostra de 10 segundos ainda não disponível. Exporte novamente após aguardar.'))
  else:story.append(p('Sem estado compatível observado. Confirmação isolada não comprova os valores posteriores; nenhum impacto foi atribuído.'))
  if item.get('overlapping_actions'):story.append(p(f"Houve {item['overlapping_actions']} outra(s) ação(ões) na janela. Os efeitos se sobrepõem; a variação não pode ser atribuída exclusivamente a esta mudança."))
  story.append(p('As diferenças também incluem a evolução normal do modelo. Clima, velocidade, demanda e rotas influenciam simultaneamente os dados. Para comparar estratégias, repita cenários com as mesmas condições iniciais.'))
 story.append(p('Retenção: até 100 ações no PDF, 1.000 amostras e 500 lotes mantidos localmente. Ações persistem entre reinícios; gráfico e lotes exibem a sessão atual. Horários reais estão em UTC; horário simulado é identificado separadamente.'))
 story.append(PageBreak())
