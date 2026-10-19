# Guia da evolução distribuída

**Anny, Arthur e Eduardo — 19/10/2026**

Este guia documenta a implementação distribuída entregue no pacote da atividade. O código público do repositório ainda corresponde à base. O [relatório acadêmico](RELATORIO_ATIVIDADE.md) reúne metodologia, resultados e referências.

## Responsabilidades

A edge executa a física do simulador original e mantém snapshots em disco. A fog usa o estado recebido, coordena a frota e calcula caminhos. O broker AMQTT executa no computador local, porta 1883, com MQTT 3.1.1 e QoS 1. A API da nuvem recebe lotes por HTTPS. A fog usa uma credencial privada própria, sem enviar chave administrativa ao painel.

| Caminho no pacote da evolução | Responsabilidade |
|---|---|
| `apps/distributed/core.py` | Store SQLite, edge, fog e campanha canário |
| `apps/distributed/runtime.py` | MQTT, serviços HTTP e envio à nuvem |
| `apps/distributed/experiments.py` | Histórico persistente de ações e amostras |
| `apps/distributed/ui-state.js` | Estados apresentados ao usuário |
| `apps/distributed/pdf_export.py` e `report_evidence.py` | PDF dinâmico e comparações |
| `supabase/functions/smartwaste-api/` | Contrato da API HTTPS |

## Caminho de uma leitura

1. A edge produz um snapshot e grava na fila.
2. Publica no tópico `smartwaste/df/snapshots`.
3. A fog armazena os eventos e confirma o snapshot em `smartwaste/df/snapshot-acks`.
4. O sincronizador da fog envia até 100 eventos por lote à API HTTPS.
5. A API valida o lote e confirma os identificadores aceitos.
6. A fog marca esses eventos como confirmados.

QoS 1 pode repetir mensagens. A deduplicação usa identificadores estáveis. A API também distingue a identidade da fog. O ACK do broker não substitui o ACK de armazenamento nem o de execução.

Os tópicos de comando são `smartwaste/df/commands` e `smartwaste/df/command-acks`. A fog reenvia enquanto não recebe confirmação. A edge registra IDs processados. Isso não fornece garantia física de exatamente uma execução após falha abrupta.

## Persistência e reinício

As filas e ações persistem em SQLite. Os contadores de envio, amostras exibidas e lotes do PDF identificam a sessão atual da fog. A física da edge não é restaurada após reinício e recebe outro `run_id`. Dados de execuções físicas diferentes não são usados como comparação antes/depois.

## Estado dos botões

O painel mostra a solicitação em andamento e usa o `command_id` para acompanhar o retorno. `APPLIED` e `DUPLICATE` confirmam o processamento. `REJECTED` mostra o motivo. Após 15 segundos sem ACK, a mensagem informa o atraso e orienta verificar MQTT e o terminal. A mensagem de envio isolada não comprova execução.

No controle de nuvem, reconectar significa habilitar o enlace e esperar uma nova confirmação de envio. Um lote iniciado antes de desconectar ainda pode concluir. A confirmação antiga não libera o aviso de uma nova reconexão.

## O que cada alteração pode influenciar

| Controle | Efeito no modelo | Cuidado ao interpretar |
|---|---|---|
| Velocidade | Ritmo do relógio simulado | Mensagens seguem a cadência real |
| Estratégia | Escolha dos próximos destinos | Caminhões já posicionados alteram o resultado |
| Clima | Velocidade e geração simuladas | Fator didático, sem calibração de campo |
| Bloqueio da EPTG | Caminhos disponíveis no grafo | Pode existir rota alternativa |
| Pausa | Suspende evolução física | Comunicação e sincronização continuam |
| Lixeira crítica | Injeta ocupação elevada | Coleta pode ocorrer antes da próxima amostra |
| Conexão da nuvem | Suspende/retoma novos envios | Fila cresce ou escoa conforme produção e envio |
| Versão de canário | Inicia teste em cinco sensores | Reversão depende da janela e dos relatos |

## Campanha canário

Cinco sensores formam o teste e 27 ficam como controle. A observação exige pelo menos dez segundos e amostras mínimas. A versão com falha simula erros. Taxa acima de 5% provoca reversão para a versão anterior de cada sensor. O nome da campanha mostra a versão testada, enquanto o estado por sensor mostra a versão efetiva. Não há gravação de firmware em hardware físico.

## PDF e retenção

O relatório registra pedido, ACK, primeira amostra compatível e nova amostra pelo menos dez segundos depois. O gráfico usa segundos reais. Datas reais e simuladas aparecem separadamente. Há aviso quando as janelas das ações se sobrepõem.

A retenção local limita ações a 500, amostras a 1.000 e lotes a 500. O PDF inclui até 100 ações e os oito últimos lotes. O histórico de leituras usa padrão de 1.000 e máximo de 10.000. Não representa exportação integral do banco remoto.

Mensagens aceitas pelo cliente MQTT não são contagem de PUBACK. Bytes são de payload e não incluem cabeçalhos TCP/TLS. Duração de lote inclui processamento e resposta, não um ping. Sem experimento com condições iniciais iguais, não se atribui economia ou desempenho a uma única configuração.

## Roteiro da apresentação

1. Iniciar o pacote distribuído com Python 3.12 e atualizar o navegador com Ctrl+F5.
2. Esperar MQTT e uma confirmação de envio à nuvem.
3. Alterar uma condição por vez e aguardar cerca de 12 segundos depois do ACK.
4. Desconectar a nuvem por pelo menos 15 segundos e observar coleta e fila.
5. Reconectar e observar novas confirmações.
6. Testar versão saudável, depois a versão com falha, e mostrar a reversão.
7. Exportar o PDF e explicar o antes/depois.

O iniciador e o JSON privado são fornecidos no pacote da atividade. Esse pacote não deve ser publicado no repositório aberto.
