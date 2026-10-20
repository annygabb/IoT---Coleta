"""Relatório PDF dos dados locais. Somente campos permitidos entram no documento."""
from io import BytesIO
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
FONTS=Path(__file__).parent/"fonts"
pdfmetrics.registerFont(TTFont("SWBody",str(FONTS/"DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("SWBold",str(FONTS/"DejaVuSans-Bold.ttf")))
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape,A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

def build_pdf(payload):
    out=BytesIO(); st=payload.get('state',{}); arc=st.get('architecture',{}); ca=st.get('canary',{}); events=payload.get('events',[])
    ink=colors.HexColor('#183B30');green=colors.HexColor('#167655');line=colors.HexColor('#CFDAD1')
    body=ParagraphStyle('body',fontName='SWBody',fontSize=9,leading=13,textColor=ink,spaceAfter=8)
    head=ParagraphStyle('head',parent=body,fontName='SWBold',fontSize=19,leading=24,spaceAfter=14,textColor=green)
    small=ParagraphStyle('small',parent=body,fontSize=7,leading=9,spaceAfter=0)
    story=[]
    def p(value,style=body):
        return Paragraph(escape(str('Sim' if value is True else 'Não' if value is False else value if value is not None else '-')).replace('\n','<br/>'),style)
    def section(title):story.extend([Spacer(1,12),p(title,head)])
    def table(rows,widths):
        t=Table([[p(v,small) for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E0EDE5')),('GRID',(0,0),(-1,-1),.3,line),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,10)])
    section('SmartWaste DF - dados da operação')
    story.append(p('Engenharia de Software - Anny, Arthur e Eduardo. Dados sintéticos de laboratório.'))
    table([['Informação','Valor'],['Exportado em UTC',payload.get('exported_at','-')],['Execução atual',arc.get('run_id')],['Horário simulado',st.get('sim_iso',st.get('sim_time','-'))],['Nuvem',arc.get('cloud_status','-')],['Última confirmação UTC',arc.get('last_sync')],['Eventos recebidos / confirmados / pendentes',f'{arc.get("received",0)} / {arc.get("synced",0)} / {arc.get("pending_cloud",0)}'],['Leituras neste relatório',f'{len(events)} (limite solicitado: {payload.get("limit",1000)}; mais recentes primeiro)'],['Estratégia / clima',f'{st.get("strategy","-")} / {st.get("weather","-")}']],[210,560])
    from .report_evidence import add_evidence
    story.append(PageBreak())
    add_evidence(story,payload,p,section,table)
    bins=st.get('bins',[])
    if bins:
        section('Ocupação das lixeiras (%)')
        drawing=Drawing(770,195);chart=VerticalBarChart();chart.x=35;chart.y=48;chart.width=720;chart.height=130;chart.data=[[b['fill_pct'] for b in bins]];chart.categoryAxis.categoryNames=[b['id'] for b in bins];chart.categoryAxis.labels.angle=45;chart.categoryAxis.labels.fontSize=6;chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=120;chart.valueAxis.valueStep=20;chart.valueAxis.labels.fontSize=7;chart.valueAxis.labels.fontName='SWBody';chart.categoryAxis.labels.fontName='SWBody';chart.bars[0].fillColor=green;drawing.add(chart);story.append(drawing)
    story.append(PageBreak());section('Lixeiras e versão em uso')
    table([['ID','Local / região','Ocupação %','Bateria %','Temp. °C','Estado','Firmware']]+[[b['id'],b['name']+' / '+b['ra'],b['fill_pct'],b['battery_pct'],b['temperature_c'],b['state'],ca.get('versions',{}).get(b['id'],'1.0')] for b in bins],[50,265,70,65,60,100,120])
    section('Caminhões')
    table([['ID','Estado','Nó atual','Destino','Carga kg','Distância km']]+[[t['id'],t['state'],t['current_node'],t.get('target_node'),t['load_kg'],t['total_distance_km']] for t in st.get('trucks',[])],[60,120,180,230,90,90])
    campaign_start=len(story)
    section('Campanha de firmware virtual')
    table([['Estado','Versão testada','Selecionados','Relatos / erros','Controle'],[ca.get('status','IDLE'),ca.get('version','1.0'),', '.join(ca.get('selected',[])),f'{ca.get("reports",0)} / {ca.get("errors",0)}',ca.get('controls',0)]],[130,120,300,130,90])
    story.append(p('A versão testada identifica a campanha. A coluna Firmware mostra a versão efetiva por sensor, inclusive após reversão. A campanha é simulada e não grava firmware físico.'))
    story[campaign_start:]=[KeepTogether(story[campaign_start:])]
    section('Histórico exportado')
    story.append(p('Últimas leituras armazenadas na fog, podendo conter mais de uma execução. Os IDs e horários identificam cada amostra. Este PDF não é uma exportação completa do banco remoto.'))
    rows=[['Identificação','Datas com fuso','Medições','Estado / versão']]
    for e in events:
        rows.append([f'Evento: {e.get("event_id","-")}\nExecução: {e.get("run_id","-")}\nDispositivo: {e.get("device_id","-")}\nLixeira: {e.get("bin_id","-")} / seq. {e.get("sequence","-")}',f'Simulado: {e.get("simulated_at","-")}\nEmitido: {e.get("emitted_at","-")}',f'Ocupação: {e.get("fill_pct","-")} %\nBateria: {e.get("battery_pct","-")} %\nTemperatura: {e.get("temperature_c","-")} °C',f'Lixeira: {e.get("operational_state","-")}\nSensor: {e.get("sensor_status","-")}\nFirmware: {e.get("firmware_version","-")}'])
    if not events:story.append(p('Ainda não há leituras. Aguarde a primeira telemetria e exporte novamente.'))
    else:table(rows,[255,240,120,155])
    def footer(canvas,doc):
        canvas.setFillColor(green);canvas.rect(0,580,842,15,fill=1,stroke=0);canvas.setFont('SWBody',8);canvas.setFillColor(ink);canvas.drawString(36,19,'SmartWaste DF - dados sintéticos');canvas.drawRightString(806,19,f'Página {doc.page}')
    doc=SimpleDocTemplate(out,pagesize=landscape(A4),leftMargin=36,rightMargin=36,topMargin=30,bottomMargin=34,title='SmartWaste DF - exportação de dados',author='Anny, Arthur e Eduardo');doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
