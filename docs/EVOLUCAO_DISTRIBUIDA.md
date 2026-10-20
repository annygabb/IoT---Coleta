# Evolução distribuída

A versão pública atual inclui a implementação, os contratos e os testes. Consulte o [guia completo da integração](ATUALIZACAO_PLATAFORMA_IOT.md) e o [estado da implementação](IMPLEMENTATION_STATUS.md).

A edge simula sensores e executa comandos. A fog coordena a frota, mantém o catálogo e os dados locais. A nuvem guarda histórico por HTTPS. O laboratório usa MQTT 3.1.1 real, QoS 1, e deduplicação na aplicação.

Na atualização de 20/10, a ingestão usa telemetria canônica 1.0, catálogo persistente, resultado individual de lote e quarentena. O histórico ordena pela medição; o último estado adaptado considera o horário real para tratar reinícios do relógio simulado.

A função de nuvem atualizada e o SQL adicional estão no repositório para revisão, sem implantação remota nesta publicação. A operação local não depende dessa implantação. Sensores canônicos novos aguardam na fila quando a função antiga responde 404.

Os dados são sintéticos. O teste de versão canário é simulado, sem gravação física de firmware. Queda da internet não equivale à parada da fog. A garantia de 72 horas sem perda ainda exige dimensionamento e teste prolongado.
