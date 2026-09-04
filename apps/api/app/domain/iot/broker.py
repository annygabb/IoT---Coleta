import json
from typing import Dict, List, Callable, Any

class VirtualMQTTBroker:
    """
    Broker MQTT virtual compatível em memória (Cap. 6.2).
    Implementa Publish/Subscribe, retenção de último estado, controle de QoS 1
    e janela de idempotência para command_id (Cap. 6.5).
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[str, Any], None]]] = {}
        self.retained_messages: Dict[str, Any] = {}
        self.processed_command_ids = set()
        self.message_history: List[Dict[str, Any]] = []
        self.total_messages_count = 0

    def subscribe(self, topic: str, handler: Callable[[str, Any], None]):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(handler)
        
        # Se houver mensagem retida, envia imediatamente ao novo assinante
        if topic in self.retained_messages:
            handler(topic, self.retained_messages[topic])

    def publish(self, topic: str, payload: Any, qos: int = 1, retain: bool = False) -> bool:
        """
        Publica uma mensagem no tópico MQTT com validação de idempotência.
        """
        # Verificação de idempotência para comandos de atuadores
        if isinstance(payload, dict) and "command_id" in payload:
            cmd_id = payload["command_id"]
            if cmd_id in self.processed_command_ids:
                # Comando duplicado rejeitado por idempotência (Cap. 6.5)
                return False
            self.processed_command_ids.add(cmd_id)
            if len(self.processed_command_ids) > 1000:
                self.processed_command_ids.pop()

        self.total_messages_count += 1
        record = {
            "seq": self.total_messages_count,
            "topic": topic,
            "payload": payload,
            "qos": qos
        }
        self.message_history.insert(0, record)
        if len(self.message_history) > 100:
            self.message_history.pop()

        if retain:
            self.retained_messages[topic] = payload

        # Disparo para assinantes diretos ou curingas simples
        for sub_topic, handlers in self.subscribers.items():
            if sub_topic == topic or sub_topic.endswith("/#") and topic.startswith(sub_topic[:-2]):
                for handler in handlers:
                    handler(topic, payload)

        return True

    def get_recent_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.message_history[:limit]
