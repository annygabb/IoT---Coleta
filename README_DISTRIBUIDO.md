# SmartWaste DF: Edge, Fog e Nuvem

> Atualização de PDF e avisos: consulte [ATUALIZACAO_PDF_AVISOS.md](docs/ATUALIZACAO_PDF_AVISOS.md). O botão Exportar PDF baixa um relatório com até 1.000 leituras locais; a exportação JSON continua na API.

**Engenharia de Software - Anny, Arthur, Eduardo e Jéssica**

A versão distribuída preserva o motor Python, as 32 lixeiras, os 3 caminhões, Dijkstra e as estratégias Fixa, Mais Próxima e VRP Smart. Edge e fog executam em processos separados e trocam mensagens MQTT 3.1.1 reais por TCP. A fog envia telemetria à nuvem por HTTPS.

## Instalação no Windows

Instale Python 3.11 ou 3.12 e abra um terminal nesta pasta.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-distributed.txt
.venv\Scripts\python run_distributed.py
```

O comando acima abre o laboratório inteiramente local, incluindo um emulador de nuvem. Internet necessária para instalar dependências. Depois, o modo local não depende da internet.

Para usar a nuvem Supabase já publicada, salve o arquivo **SmartWaste_Conexao_Privada.json**, entregue separadamente, nesta pasta e execute:

```powershell
.venv\Scripts\python run_distributed.py --cloud-config SmartWaste_Conexao_Privada.json
```

O painel abre em http://127.0.0.1:8000. Mantenha o terminal aberto. Ctrl+C encerra os serviços iniciados. As portas 1883, 8000, 8001 e 8002 precisam estar disponíveis. O modo Supabase não inicia a porta 8002.

Linux/macOS: use `.venv/bin/python` no lugar de `.venv\Scripts\python`.

## Arquitetura e motivo

| Camada | Processo / arquivo | Responsabilidade | Por quê |
|---|---|---|---|
| Edge | runtime.py / edge_app | Simula sensores, movimento, coleta e comandos | A execução física pertence ao dispositivo |
| Broker | broker.py, porta 1883 | Encaminha publicações e assinaturas MQTT | Permite comunicação real entre processos |
| Fog | runtime.py / fog_app | Recebe snapshots, decide rotas, mantém fila e painel | Precisa da visão conjunta da frota, mesmo sem internet |
| Nuvem | smartwaste-api, Supabase | Valida e armazena histórico em Postgres | Centraliza dados sem controlar a operação local |

O nome comercial "Edge Functions" do Supabase não define o papel no nosso desenho: aqui, a função hospedada representa a **nuvem**. Não executamos o motor Python dentro dela.

A nova interface consulta o estado da fog a cada segundo. A interface anterior permanece em `/legacy`, como demonstração independente. Não use as duas para comparar a mesma execução: a antiga possui simulação própria.

## Comunicação e garantias

Tópicos: `smartwaste/df/snapshots`, `snapshot-acks`, `commands`, `command-acks`. MQTT QoS 1 pode repetir mensagens. A aplicação usa IDs e confirmações adicionais para evitar registros duplicados.

A edge grava cada snapshot em SQLite antes do envio. A fog grava o lote inteiro antes de confirmar. A fog mantém eventos na fila até receber IDs confirmados pela nuvem. O Supabase impõe unicidade em `(fog_id,event_id)`. Reenvios mantêm o mesmo ID.

O PUBACK do MQTT confirma uma etapa do protocolo com o broker. A confirmação da aplicação informa que a fog gravou os dados ou que a edge aplicou o comando. Não são a mesma coisa. Confirmar um comando de rota significa aceitar/aplicar a rota, não concluir a coleta.

A fog preserva o histórico de snapshots atrasados, mas não substitui seu estado mais novo por uma sequência menor da mesma execução. Cada boot da edge cria um `run_id` novo.

## Segurança e configuração

O broker aceita conexão anônima **somente em 127.0.0.1**. As APIs locais também escutam apenas nessa interface. Para dispositivos físicos em rede, configurar autenticação MQTT, ACL por tópico e TLS antes de mudar o bind. Não exponha este laboratório diretamente na internet.

A API hospedada exige `x-fog-token` para ingestão e consulta. A configuração privada contém esse segredo. Não a publique em GitHub, nos slides ou em capturas. A chave administrativa Supabase fica no ambiente da função, nunca no painel ou no ZIP. A identidade da fog deriva da credencial, não do corpo enviado pelo cliente.

Tabelas com RLS habilitado e sem acesso de `anon`/`authenticated`. A função acessa o banco por credencial interna. `/health` é público e não revela dados privados.

## Demonstração

1. Aguarde aparecerem leituras e confirmações da nuvem.
2. Clique **Desconectar nuvem**. Observe horário e caminhões avançando e pendências aumentando.
3. Clique **Reconectar nuvem**. Aguarde a fila diminuir conforme a nuvem confirma lotes.
4. Teste **Versão com falha**. Cinco sensores ficam no canário e 27 no controle. Após a janela de observação, o grupo reverte para versão 1.0.
5. Clique Exportar PDF para baixar o resumo e até 1.000 leituras locais. A API /api/export mantém o JSON com até 10 mil eventos para análises.

O canário é simulado. Observa pelo menos 10 segundos, pelo menos 5 relatos do grupo e 5 do controle. Mais de 5% de erros no grupo causa ROLLBACK. A versão saudável libera uma próxima onda manual. Não há gravação de flash, assinatura de firmware nem OTA física.

## Gratuidade e limites

O projeto `smartwaste-df` está na organização **annygabb's Org**, região **sa-east-1 (São Paulo)**, plano Free. Não foi contratado plano pago. O broker local não tem mensalidade de hospedagem, mas usa energia e recursos do seu computador.

O plano Free tem cotas. Consulte https://supabase.com/pricing antes de expandir. Em 19/10/2026: 500 MB de banco, 5 GB de saída e pausa após uma semana de inatividade. Não há garantia de disponibilidade contínua. Sem upgrade automático autorizado.

Amostragem local: 32 eventos por segundo real. No modo Supabase, `telemetry_every=5` guarda 32 eventos a cada cinco snapshots (aproximadamente 6,4 eventos/s). O painel e a coordenação local continuam recebendo snapshots a cada segundo. Isso reduz a pressão sobre o enlace e as cotas, mas pode omitir mudanças transitórias do histórico remoto. Alertas prioritários são uma evolução necessária para uso real. No modo local contínuo, são cerca de 2,76 milhões de eventos/dia. Com amostragem remota de cinco snapshots, são aproximadamente 552.960 eventos/dia. Esse ritmo pode esgotar o banco gratuito rapidamente. Use sessões curtas e exporte o histórico. Para implantação contínua, medir volume e ajustar amostragem, agregação e retenção. Esta entrega não apaga histórico automaticamente.

## Limitações conhecidas

- Sensores e caminhões são virtuais. Economia, combustível e CO₂ são estimativas didáticas.
- A fila e o histórico persistem, mas a posição física e a campanha canário reiniciam com a edge. Não há restauração integral do digital twin.
- A fila de comandos pendentes na fog reside em memória. Requer recuperação operacional adicional em produção.
- Idempotência do comando não garante execução física exatamente uma vez em uma queda entre atuar e gravar a confirmação.
- A fila tem limite de 100 mil itens pendentes. Ao atingir o limite, expõe erro e deixa de confirmar novos lotes. Disco finito não suporta retenção ilimitada. Eventos confirmados ficam no histórico local e também consomem disco.
- O emulador local agora valida eventos e resultados individuais. A função hospedada anterior permanece sem atualização remota nesta entrega; consulte `docs/ATUALIZACAO_PLATAFORMA_IOT.md`.
- A ingestão local separa erros em quarentena. Rejeições permanentes individualizadas pela função preparada também são isoladas. Falhas não individualizadas da função hospedada anterior permanecem pendentes para diagnóstico.
- O botão de desconexão simula falha do enlace com a nuvem, não queda de energia ou perda física de disco.
- A revisão visual automatizada do painel em navegador não foi concluída neste ambiente. Os controles têm verificação via API. Confira o layout no seu navegador antes da apresentação.

## Testes e evidências

```powershell
.venv\Scripts\python -m pytest -q
node --test supabase/functions/smartwaste-api/core.test.mjs
.venv\Scripts\python scripts/run_evidence.py
.venv\Scripts\python scripts/run_evidence.py --cloud-config SmartWaste_Conexao_Privada.json --output docs/evidence-remote
```

`docs/evidence*/` guarda CSV, JSON e log da execução. Os testes não usam placas reais. O Node só é necessário para testar a validação da função de nuvem. A aplicação local utiliza Python.

O primeiro teste remoto com 32 eventos/s não drenou a fila: as chamadas levaram aproximadamente 6 a 8 segundos. Essa medição motivou a amostragem do histórico remoto. Consulte as evidências finais para o resultado da configuração ajustada.

## Publicação e manutenção

A nuvem publicada é uma API e um banco, não o painel completo hospedado. O painel continua local. Dashboard do projeto: https://supabase.com/dashboard/project/glyvjheauocycvwieytr

Health público: https://glyvjheauocycvwieytr.supabase.co/functions/v1/smartwaste-api/health

Código da função em `supabase/functions/smartwaste-api/`. Para republicar, usar Supabase CLI autenticada e projeto vinculado. Manter `verify_jwt=false` apenas com a autenticação própria por `x-fog-token` preservada. Nunca remover a validação do token.

Para revogar a conexão entregue, desabilitar a credencial `fog-df-01` na tabela `smartwaste_credentials`. Para rotação, gerar token aleatório novo, guardar apenas SHA-256 dele no banco e atualizar a configuração privada local.

Leia `docs/EDGE_FOG_NUVEM.md` e o relatório PDF para explicações completas, imagens, resultados e roteiro de apresentação.
