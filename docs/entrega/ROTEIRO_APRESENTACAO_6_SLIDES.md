# SmartWaste DF — roteiro da apresentação em 6 slides

**Engenharia de Software — Anny, Arthur, Eduardo e Jéssica**

[Baixar PowerPoint editável](SmartWaste_Apresentacao_Resumida_6_Slides.pptx)

Tempo sugerido: de 4 a 6 minutos. Os termos técnicos necessários estão definidos no próprio slide.

## 1. Coleta inteligente, do sensor à nuvem
“O nosso projeto simula 32 lixeiras e três caminhões. IoT significa dispositivos que trocam dados. Evoluímos a comunicação e o armazenamento para que as decisões locais possam continuar durante uma interrupção da internet. Os sensores e veículos desta demonstração são virtuais.”

## 2. Três camadas
“A edge faz a medição e executa comandos. A fog fica no computador local, decide rotas e atende o painel. A nuvem guarda o histórico remoto. MQTT é a troca de mensagens entre a ponta e a fog; o broker encaminha essas mensagens. HTTPS protege o envio pela internet. Supabase é o serviço usado na integração de nuvem.”

Um exemplo: a lixeira informa seu nível; a fog avalia a coleta e envia o comando; a edge executa. A fog também envia as leituras ao histórico remoto.

## 3. Falha de internet
“A falta de internet interrompe a atualização remota, mas as leituras ficam na fila local. SQLite é o banco em arquivo usado para guardar os dados. Quando a conexão volta, a fog reenvia grupos de leituras, chamados lotes. O identificador estável de cada leitura permite reconhecer repetições.”

Explique a condição: computador, fog, broker e comunicação local precisam continuar funcionando. A fila tem limites, usa disco e não elimina falhas físicas. Pendente indica espera: não é confirmação de perda nem de recebimento pela nuvem.

## 4. Melhorias nos dados
“O contrato canônico dá às mensagens uma estrutura comum. O catálogo registra os sensores e seus locais; o perfil define o que cada tipo de sensor pode medir. A API é a interface usada por outros programas para cadastrar ou enviar dados. A quarentena isola mensagens inválidas e registra o motivo, permitindo que as válidas avancem.”

“Uma leitura antiga que chega depois completa o histórico. Ela não substitui o estado atual de uma leitura mais recente.” Exemplo ilustrativo: uma leitura medida às 13h chega depois da leitura das 14h; o painel conserva o estado das 14h. Isso evita que o atraso da comunicação pareça uma mudança atual do sensor.

## 5. Teste de validação
“No teste registrado no projeto, enviamos 5.000 mensagens sintéticas. Foram aceitas 4.997; três ficaram em quarentena, com o motivo do erro. O benefício demonstrado é processar as mensagens válidas mesmo quando algumas apresentam problemas.”

Os percentuais são 99,94% aceitas e 0,06% isoladas. A barra usa a mesma escala: a faixa de três mensagens é muito estreita, por isso o número aparece em destaque. Esses resultados descrevem esse lote, não garantem uma taxa de confiabilidade em produção. Não foram medidos ganhos reais de combustível ou bateria.

## 6. Ganhos, custos e próximo passo
“O ganho é organizar melhor os dados e manter as decisões perto dos sensores. A contrapartida é cuidar de mais processos e de armazenamento local. Durante a falta de internet, o histórico remoto fica atrasado. O plano Free do Supabase possui cotas.”

“Os registros da implementação informam 60 testes Python e 28 JavaScript aprovados. O novo fluxo de sensores foi validado localmente, mas sua implantação remota permanece pendente. A integração anterior de lixeiras e a proposta nova de sensores precisam ser distinguidas.”

Esses números foram obtidos na validação da implementação; os testes do sistema não foram executados novamente para criar esta apresentação. O conteúdo foi conferido com o README público na revisão ef7ef8c8fa413898b8c84122a6c0f0ea9bd30275.

## Arquivo e conferência
A apresentação tem seis páginas em formato 16:9, com textos, blocos, diagramas e barras editáveis. O link do GitHub é clicável no último slide. Nenhuma credencial está incluída.

Foram conferidos: contagem de slides, integridade ZIP, estrutura XML, destinos dos relacionamentos e limites de página dos elementos. A renderização visual no PowerPoint não pôde ser executada no ambiente desta geração. Abra o arquivo para conferir a aparência antes de apresentar.

Para gerar PDF no PowerPoint: **Arquivo → Exportar → Criar PDF/XPS**. O PDF anterior do repositório corresponde à apresentação completa de 14 slides.

Projeto: https://github.com/annygabb/IoT---Coleta
