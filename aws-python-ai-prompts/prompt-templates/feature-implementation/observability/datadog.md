# Implementação de Observabilidade com Datadog

Este prompt auxilia na configuração e integração do Datadog para monitoramento, métricas e tracing em aplicações AWS Lambda e ECS.

## Contexto para IA

```
Você irá implementar instrumentação e observabilidade usando Datadog para uma aplicação 
AWS Python. A instrumentação deve incluir configuração do tracer, métricas personalizadas,
logs estruturados e spans para operações importantes, seguindo boas práticas.
```

## Prompt Base

```
Implemente instrumentação de observabilidade usando Datadog para {TIPO_APLICACAO}.

Requisitos:
- Configure o tracer do Datadog para a aplicação
- Implemente métricas personalizadas para operações críticas
- Adicione logs estruturados com correlação a traces
- Crie spans personalizados para medir o desempenho de operações específicas
- Implemente tags consistentes para filtrar métricas e logs
- Configure alertas para condições críticas
- {REQUISITO_ADICIONAL}

Componentes a serem instrumentados:
```python
{CODIGO_COMPONENTES}
```

Contexto adicional sobre a aplicação:
{CONTEXTO_APLICACAO}
```

## Exemplo Preenchido

```
Implemente instrumentação de observabilidade usando Datadog para uma AWS Lambda que processa pedidos.

Requisitos:
- Configure o tracer do Datadog para a aplicação Lambda
- Implemente métricas personalizadas para contagem de pedidos processados, falhas e latência
- Adicione logs estruturados com correlação a traces
- Crie spans personalizados para medir o desempenho das etapas de processamento
- Implemente tags consistentes para filtrar métricas e logs (cliente_id, status, etc.)
- Configure alertas para taxas de erro acima de 5% e latência acima de 2 segundos
- Considere a visibilidade de cold starts em Lambdas

Componentes a serem instrumentados:
```python
# handler.py
import json
from application.usecases.processar_pedido_usecase import ProcessarPedidoUseCase
from application.dtos.pedido_dto import PedidoDTO
from config.di_container import container

def lambda_handler(event, context):
    try:
        # Processar mensagens do SQS
        for record in event['Records']:
            # Extrair corpo da mensagem
            message_body = json.loads(record['body'])
            
            # Converter para DTO
            pedido_dto = PedidoDTO(**message_body)
            
            # Obter caso de uso do container DI
            use_case = container.resolve(ProcessarPedidoUseCase)
            
            # Executar caso de uso
            result = use_case.execute(pedido_dto)
            
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processamento concluído com sucesso'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# application/usecases/processar_pedido_usecase.py
class ProcessarPedidoUseCase:
    def __init__(
        self, 
        pedido_repo: IPedidoRepository, 
        notificacao_gateway: INotificacaoGateway,
        logger: ILogger
    ):
        self.pedido_repo = pedido_repo
        self.notificacao_gateway = notificacao_gateway
        self.logger = logger
        
    def execute(self, pedido_dto: PedidoDTO) -> PedidoResponseDTO:
        self.logger.info(f"Processando pedido para cliente {pedido_dto.cliente_id}")
        
        # Converte DTO para entidade
        pedido = Pedido.from_dict(pedido_dto.dict())
        
        # Calcula o total
        total = pedido.calcular_total()
        
        # Persiste no repositório
        self.pedido_repo.salvar(pedido)
        
        # Marca como processado
        pedido.marcar_como_processado()
        self.pedido_repo.atualizar_status(pedido.id, pedido.status)
        
        # Notifica
        self.notificacao_gateway.enviar_notificacao(
            pedido_dto.cliente_id,
            f"Pedido {pedido.id} processado com sucesso. Total: {total}"
        )
        
        # Retorna DTO de resposta
        return PedidoResponseDTO(
            pedido_id=pedido.id,
            status=pedido.status.value,
            valor_total=float(total)
        )
```

Contexto adicional sobre a aplicação:
A aplicação é uma função Lambda que processa pedidos recebidos via SQS, salva-os no DynamoDB e envia notificações. Métricas importantes incluem o tempo de processamento total, erros por tipo, e latência de cada operação (conversão, persistência, notificação). Quero monitorar especificamente erros de conexão com o DynamoDB e falhas na comunicação com o serviço de notificação.
```

## Como Adaptar

Para usar este template:

1. Substitua `{TIPO_APLICACAO}` por AWS Lambda, ECS, Fargate, etc.
2. Cole o código dos componentes a serem instrumentados em `{CODIGO_COMPONENTES}`
3. Descreva o contexto da aplicação em `{CONTEXTO_APLICACAO}`
4. Adicione requisitos específicos em `{REQUISITO_ADICIONAL}`, se necessário

## Output Esperado

A IA deve gerar:

1. **Configuração básica do Datadog** para a plataforma especificada, por exemplo:

```python
# config/datadog_config.py
import os
from functools import wraps
from ddtrace import patch_all, tracer, config
import logging
from datadog import initialize, statsd

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_datadog():
    """Configuração inicial do Datadog."""
    # Configurar tags de ambiente
    env = os.environ.get("ENVIRONMENT", "dev")
    service = os.environ.get("DD_SERVICE", "pedido-processor")
    
    # Configurar tracer
    config.env = env
    config.service = service
    
    # Patch automático de bibliotecas
    patch_all()
    
    # Configurar DogStatsD para métricas
    initialize(statsd_host=os.environ.get("DD_AGENT_HOST", "localhost"),
               statsd_port=int(os.environ.get("DD_STATSD_PORT", "8125")))
    
    logger.info(f"Datadog inicializado: env={env}, service={service}")

# Decorator para adicionar tracing aos métodos    
def trace_method(name=None, service=None, resource=None, tags=None):
    """Decorator para adicionar tracing aos métodos."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extrair self se for um método de classe
            operation_name = name
            if not operation_name and len(args) > 0 and hasattr(args[0], '__class__'):
                cls_name = args[0].__class__.__name__
                operation_name = f"{cls_name}.{func.__name__}"
            
            span_kwargs = {
                'name': operation_name or func.__name__,
                'service': service,
                'resource': resource or operation_name or func.__name__,
                'tags': tags or {}
            }
            
            with tracer.trace(**span_kwargs) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_tag('status', 'success')
                    return result
                except Exception as e:
                    span.set_tag('status', 'error')
                    span.set_tag('error.type', type(e).__name__)
                    span.set_tag('error.msg', str(e))
                    span.set_tag('error.stack', logging.format_exception(*sys.exc_info()))
                    raise
        return wrapper
    return decorator
```

2. **Instrumentação do handler** (para Lambda) ou entry point:

```python
# handler.py
import json
import time
from ddtrace import tracer, config
from datadog import statsd
from config.datadog_config import setup_datadog
from application.usecases.processar_pedido_usecase import ProcessarPedidoUseCase
from application.dtos.pedido_dto import PedidoDTO
from config.di_container import container
import logging

logger = logging.getLogger(__name__)

# Executar setup no módulo import (cold start)
setup_datadog()

def lambda_handler(event, context):
    # Registrar início do processamento + cold start
    is_cold_start = getattr(lambda_handler, '_cold_start', True)
    if is_cold_start:
        statsd.increment('lambda.cold_start', 1)
        lambda_handler._cold_start = False
    
    # Iniciar span root da requisição
    with tracer.trace('lambda.handler', service='pedido-processor', resource='lambda_handler') as span:
        try:
            span.set_tag('aws.requestId', context.aws_request_id)
            span.set_tag('function_name', context.function_name)
            span.set_tag('records_count', len(event.get('Records', [])))
            
            start_time = time.time()
            
            # Contador de sucessos/falhas
            success_count = 0
            error_count = 0
            
            # Processar mensagens do SQS
            for record in event.get('Records', []):
                with tracer.trace('process.message', service='pedido-processor') as msg_span:
                    try:
                        # Adicionar metadados da mensagem ao span
                        msg_span.set_tag('message.id', record.get('messageId', 'unknown'))
                        
                        # Extrair corpo da mensagem
                        message_body = json.loads(record['body'])
                        
                        # Logger estruturado (correlacionado com trace)
                        logger.info(f"Processando mensagem", extra={
                            'message_id': record.get('messageId'),
                            'cliente_id': message_body.get('cliente_id')
                        })
                        
                        # Converter para DTO
                        pedido_dto = PedidoDTO(**message_body)
                        msg_span.set_tag('cliente_id', pedido_dto.cliente_id)
                        
                        # Obter caso de uso do container DI
                        use_case = container.resolve(ProcessarPedidoUseCase)
                        
                        # Executar caso de uso
                        with statsd.timed('pedido.process_time', tags=[
                            f'cliente:{pedido_dto.cliente_id}'
                        ]):
                            result = use_case.execute(pedido_dto)
                        
                        # Registrar sucesso
                        statsd.increment('pedido.processed', tags=[
                            f'cliente:{pedido_dto.cliente_id}',
                            f'status:{result.status}'
                        ])
                        success_count += 1
                        
                    except Exception as e:
                        # Registrar erro
                        error_count += 1
                        logger.exception(f"Erro ao processar mensagem: {str(e)}", extra={
                            'message_id': record.get('messageId', 'unknown'),
                            'error_type': type(e).__name__
                        })
                        statsd.increment('pedido.error', tags=[
                            f'error_type:{type(e).__name__}'
                        ])
                        # Não propagar exceção para processar as demais mensagens
            
            # Métricas de duração da função
            execution_time = (time.time() - start_time) * 1000
            statsd.histogram('lambda.execution_time', execution_time)
            
            # Agregar métricas
            span.set_tag('success_count', success_count)
            span.set_tag('error_count', error_count)
            
            # Retornar resultados
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'processedMessages': success_count,
                    'failedMessages': error_count
                })
            }
        except Exception as e:
            # Erro na função como um todo
            logger.exception(f"Erro crítico no handler: {str(e)}")
            statsd.increment('lambda.critical_error', tags=[
                f'error_type:{type(e).__name__}'
            ])
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
```

3. **Instrumentação do caso de uso**:

```python
# application/usecases/processar_pedido_usecase.py
from ddtrace import tracer
from datadog import statsd
from config.datadog_config import trace_method
import logging

logger = logging.getLogger(__name__)

class ProcessarPedidoUseCase:
    def __init__(
        self, 
        pedido_repo: IPedidoRepository, 
        notificacao_gateway: INotificacaoGateway,
        logger: ILogger
    ):
        self.pedido_repo = pedido_repo
        self.notificacao_gateway = notificacao_gateway
        self.logger = logger
    
    @trace_method(tags={'operation_type': 'process_order'})
    def execute(self, pedido_dto: PedidoDTO) -> PedidoResponseDTO:
        try:
            # Adicionar cliente_id ao span atual para contexto
            current_span = tracer.current_span()
            if current_span:
                current_span.set_tag('cliente_id', pedido_dto.cliente_id)
                
            # Log estruturado (correlacionado com trace)
            self.logger.info(f"Processando pedido", extra={
                'cliente_id': pedido_dto.cliente_id,
                'items_count': len(pedido_dto.itens)
            })
            
            # Converte DTO para entidade (com trace)
            with tracer.trace('pedido.convert_dto') as span:
                pedido = Pedido.from_dict(pedido_dto.dict())
                span.set_tag('pedido_id', pedido.id)
            
            # Calcula o total
            with tracer.trace('pedido.calcular_total') as span:
                total = pedido.calcular_total()
                span.set_tag('valor_total', float(total))
            
            # Persiste no repositório
            with tracer.trace('pedido.persistir') as span:
                start = time.time()
                self.pedido_repo.salvar(pedido)
                duracao_ms = (time.time() - start) * 1000
                span.set_tag('duracao_ms', duracao_ms)
                
                # Registrar latência do DynamoDB
                statsd.histogram('repository.save_latency', duracao_ms, tags=[
                    'operation:save_pedido'
                ])
            
            # Marca como processado
            pedido.marcar_como_processado()
            
            with tracer.trace('pedido.atualizar_status') as span:
                self.pedido_repo.atualizar_status(pedido.id, pedido.status)
                span.set_tag('status', pedido.status.value)
            
            # Notifica
            with tracer.trace('pedido.notificar') as span:
                self.notificacao_gateway.enviar_notificacao(
                    pedido_dto.cliente_id,
                    f"Pedido {pedido.id} processado com sucesso. Total: {total}"
                )
                span.set_tag('notification_sent', True)
            
            # Métrica de pedido processado com sucesso
            statsd.increment('pedido.success', tags=[
                f'cliente:{pedido_dto.cliente_id}'
            ])
            
            # Retorna DTO de resposta
            return PedidoResponseDTO(
                pedido_id=pedido.id,
                status=pedido.status.value,
                valor_total=float(total)
            )
            
        except Exception as e:
            # Registrar erro com tipo específico para alertas
            self.logger.error(f"Erro ao processar pedido: {str(e)}", extra={
                'cliente_id': pedido_dto.cliente_id,
                'error_type': type(e).__name__
            })
            
            # Incrementar contador de erros com tags para diferentes tipos
            statsd.increment('pedido.error', tags=[
                f'cliente:{pedido_dto.cliente_id}',
                f'error_type:{type(e).__name__}'
            ])
            
            # Propagar exceção
            raise
```

4. **Configuração de variáveis de ambiente** (para Lambda ou ECS):

```
# Para Lambda (serverless.yml)
environment:
  DD_TRACE_ENABLED: "true"
  DD_ENV: "${self:custom.stage}"
  DD_SERVICE: "pedido-processor"
  DD_VERSION: "${self:custom.version}"
  DD_LOGS_INJECTION: "true"
  DD_TRACE_SAMPLE_RATE: "1.0"
  DD_APPSEC_ENABLED: "true"
  DD_LAMBDA_HANDLER: "handler.lambda_handler"

# Ou para ECS (docker-compose.yml ou Terraform)
environment:
  - DD_TRACE_ENABLED=true
  - DD_ENV=prod
  - DD_SERVICE=pedido-processor
  - DD_VERSION=1.0.0
  - DD_LOGS_INJECTION=true
  - DD_TRACE_SAMPLE_RATE=1.0
  - DD_APPSEC_ENABLED=true
  - DD_AGENT_HOST=datadog-agent
  - DD_STATSD_PORT=8125
```

## Boas Práticas de Observabilidade

1. **The Three Pillars**
   - **Logs**: Use logs estruturados e correlacione com trace IDs
   - **Métricas**: Combine métricas de contador, histograma e gauge
   - **Traces**: Use spans personalizados para medir operações importantes

2. **Tags Consistentes**
   - Aplique tags consistentes em logs, métricas e traces
   - Use convenções de nomenclatura padronizadas

3. **Errors & Alerting**
   - Categorize erros por tipo para melhor diagnóstico
   - Configure alertas para condições críticas

4. **Performance**
   - Meça latências de operações críticas
   - Use histogramas para visualizar distribuições

5. **Instrumentação por Ambiente**
   - Adaptação específica para AWS Lambda, ECS e outros serviços
   - Considerações para cold starts, timeouts e retries

## Configurações Específicas para AWS Lambda

1. **Extensão Datadog**
   - Habilite a extensão Datadog via Layer
   - Configure nível de rastreamento adequado para seu ambiente

```yaml
# serverless.yml
functions:
  processOrder:
    handler: handler.lambda_handler
    layers:
      - !Sub arn:aws:lambda:${AWS::Region}:464622532012:layer:Datadog-Extension:38
    environment:
      DD_LAMBDA_HANDLER: handler.lambda_handler
      DD_TRACE_ENABLED: true
```

2. **Métricas Lambda-específicas**
   - Cold starts
   - Uso de memória
   - Timeouts
   - Erros por tipo

## Configurações Específicas para ECS/Fargate

1. **Agent de Monitoramento**
   - Sidecar Datadog Agent para coletar métricas
   - Configuração de APM e log collection

```yaml
# docker-compose.yml (exemplo)
services:
  pedido-app:
    image: pedido-processor:latest
    depends_on:
      - datadog-agent
    environment:
      - DD_AGENT_HOST=datadog-agent
      - DD_TRACE_AGENT_PORT=8126
      
  datadog-agent:
    image: gcr.io/datadoghq/agent:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_LOGS_ENABLED=true
      - DD_APM_ENABLED=true
      - DD_APM_NON_LOCAL_TRAFFIC=true
``` 