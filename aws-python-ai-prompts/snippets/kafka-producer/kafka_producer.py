import json
import logging
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import time

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError

logger = logging.getLogger(__name__)

@dataclass
class KafkaMessage:
    """Representação de uma mensagem Kafka."""
    key: Optional[str]
    value: Dict[str, Any]
    headers: Optional[List[tuple]] = None
    
    def __post_init__(self):
        # Garantir que headers esteja no formato correto se fornecido
        if self.headers:
            self.headers = [(k, v.encode() if isinstance(v, str) else v) 
                           for k, v in self.headers]

class KafkaProducerWrapper:
    """
    Wrapper para KafkaProducer com recursos adicionais para uso com AWS MSK.
    """
    
    def __init__(
        self,
        bootstrap_servers: Union[str, List[str]],
        serializer_type: str = "json",
        acks: str = "all",
        retries: int = 3,
        linger_ms: int = 5,
        compression_type: str = "gzip",
        batch_size: int = 16384,
        **additional_config
    ):
        """
        Inicializa o produtor Kafka.
        
        Args:
            bootstrap_servers: Lista de servidores Kafka (brokers)
            serializer_type: Tipo de serialização ('json' ou 'avro')
            acks: Configuração de confirmações ('0', '1', 'all')
            retries: Número de retentativas em caso de falha
            linger_ms: Atraso (ms) para acumular mensagens em batch
            compression_type: Tipo de compressão ('gzip', 'snappy', 'lz4')
            batch_size: Tamanho máximo do batch em bytes
            additional_config: Configurações adicionais para o KafkaProducer
        """
        self.serializer_type = serializer_type
        
        # Configuração básica do produtor
        config = {
            'bootstrap_servers': bootstrap_servers,
            'acks': acks,
            'retries': retries,
            'linger_ms': linger_ms,
            'compression_type': compression_type,
            'batch_size': batch_size,
            'api_version': (2, 0, 0),  # Compatível com a maioria das versões MSK
        }
        
        # Configurar serialização
        if serializer_type == "json":
            config['value_serializer'] = lambda v: json.dumps(v).encode('utf-8')
            config['key_serializer'] = lambda k: k.encode('utf-8') if k else None
        elif serializer_type == "avro":
            # Para usar Avro, é necessário definir Schema Registry
            try:
                from confluent_kafka.avro.serializer import AvroSerializer
                from confluent_kafka.schema_registry import SchemaRegistryClient
                
                schema_registry_url = additional_config.pop('schema_registry_url', 
                                    os.environ.get('SCHEMA_REGISTRY_URL'))
                value_schema = additional_config.pop('value_schema')
                key_schema = additional_config.pop('key_schema', None)
                
                schema_registry_conf = {'url': schema_registry_url}
                schema_registry_client = SchemaRegistryClient(schema_registry_conf)
                
                config['value_serializer'] = AvroSerializer(
                    schema_registry_client, value_schema
                )
                
                if key_schema:
                    config['key_serializer'] = AvroSerializer(
                        schema_registry_client, key_schema
                    )
            except ImportError:
                raise ImportError("Para usar serialização Avro, instale confluent-kafka")
            except KeyError:
                raise ValueError("Para usar Avro, forneça schema_registry_url e value_schema")
        else:
            raise ValueError(f"Tipo de serialização não suportado: {serializer_type}")
        
        # Configurações de SSL para MSK (opcional, ativada se as variáveis existirem)
        if os.environ.get('MSK_SSL_ENABLED', 'false').lower() == 'true':
            ssl_config = {
                'security_protocol': 'SSL',
                'ssl_check_hostname': True,
                'ssl_cafile': os.environ.get('MSK_SSL_CA_LOCATION'),
                'ssl_certfile': os.environ.get('MSK_SSL_CERT_LOCATION'),
                'ssl_keyfile': os.environ.get('MSK_SSL_KEY_LOCATION'),
            }
            config.update(ssl_config)
        
        # Adicionar configurações extras
        config.update(additional_config)
        
        # Inicializar o produtor
        self.producer = KafkaProducer(**config)
        logger.info(f"Kafka producer iniciado com {bootstrap_servers}")
    
    def send_message(
        self, 
        topic: str, 
        message: KafkaMessage,
        sync: bool = False,
        timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Envia uma mensagem para um tópico Kafka.
        
        Args:
            topic: Nome do tópico Kafka
            message: Objeto KafkaMessage contendo key, value e headers
            sync: Se True, espera confirmação da mensagem (bloqueante)
            timeout: Timeout em segundos para envio síncrono
            
        Returns:
            Metadata do record se sync=True, None caso contrário
        """
        try:
            future = self.producer.send(
                topic=topic,
                key=message.key,
                value=message.value,
                headers=message.headers
            )
            
            logger.debug(f"Mensagem enviada para {topic}", 
                        extra={"key": message.key, "message_size": len(str(message.value))})
            
            if sync:
                # Modo síncrono - esperar confirmação
                record_metadata = future.get(timeout=timeout)
                logger.info(
                    f"Mensagem confirmada: {topic} [partition={record_metadata.partition}, offset={record_metadata.offset}]",
                    extra={"key": message.key}
                )
                return {
                    "topic": record_metadata.topic,
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset,
                    "timestamp": record_metadata.timestamp
                }
            return None
            
        except KafkaTimeoutError:
            logger.error(f"Timeout ao enviar mensagem para {topic}", 
                        extra={"key": message.key})
            raise
        except KafkaError as e:
            logger.error(f"Erro ao enviar mensagem para {topic}: {str(e)}", 
                        extra={"key": message.key})
            raise
    
    def send_messages_batch(
        self, 
        topic: str, 
        messages: List[KafkaMessage],
        sync: bool = False,
        timeout: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Envia um lote de mensagens para um tópico Kafka.
        
        Args:
            topic: Nome do tópico
            messages: Lista de objetos KafkaMessage
            sync: Se True, espera confirmação de todas as mensagens
            timeout: Timeout em segundos para envio síncrono
            
        Returns:
            Lista de metadados das mensagens se sync=True, lista vazia caso contrário
        """
        futures = []
        
        try:
            # Enviar todas as mensagens
            start_time = time.time()
            for message in messages:
                future = self.producer.send(
                    topic=topic,
                    key=message.key,
                    value=message.value,
                    headers=message.headers
                )
                futures.append((message.key, future))
            
            logger.info(f"Batch de {len(messages)} mensagens enviado para {topic}")
            
            if not sync:
                return []
            
            # Em modo síncrono, esperar todas as confirmações
            results = []
            for key, future in futures:
                time_left = timeout - (time.time() - start_time)
                if time_left <= 0:
                    raise KafkaTimeoutError(f"Timeout ao aguardar confirmação do batch")
                
                record_metadata = future.get(timeout=time_left)
                results.append({
                    "key": key,
                    "topic": record_metadata.topic,
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset,
                    "timestamp": record_metadata.timestamp
                })
            
            logger.info(f"Batch de {len(messages)} mensagens confirmado para {topic}")
            return results
                
        except KafkaTimeoutError:
            logger.error(f"Timeout ao enviar batch para {topic}")
            raise
        except KafkaError as e:
            logger.error(f"Erro ao enviar batch para {topic}: {str(e)}")
            raise
    
    def flush(self, timeout: float = 10.0) -> None:
        """Força o envio de todas as mensagens pendentes."""
        self.producer.flush(timeout=timeout)
        
    def close(self, timeout: float = 10.0) -> None:
        """Fecha o produtor, enviando todas as mensagens pendentes."""
        self.producer.flush(timeout=timeout)
        self.producer.close(timeout=timeout)
        logger.info("Kafka producer fechado") 