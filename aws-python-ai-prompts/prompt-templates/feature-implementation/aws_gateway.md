# Implementação de Repository

Este prompt auxilia na criação de gateways e repositórios para serviços AWS (S3, DynamoDB, RDS, etc.) seguindo Clean Architecture.

## Contexto para IA

```
Você irá implementar um repositório para um serviço AWS específico. 
A implementação deve seguir Clean Architecture, com interfaces no domínio e 
implementações concretas na infraestrutura, mantendo o domínio livre de 
dependências externas.
```

## Prompt Base

```
Implemente um gateway para acesso ao serviço {SERVICO_AWS} usando `boto3`.

Requisitos:
- Interface no `domain/gateways` ou `domain/repositories` (conforme apropriado)
- Implementação concreta em `infrastructure/gateways` ou `infrastructure/repositories`
- Tratamento de erros e logging com Datadog
- Tipagem completa usando type hints
- Retry com `botocore` ou lib auxiliar (como tenacity)
- Teste unitário com mocks (`moto` se suportado)

Operações necessárias:
- {OPERACAO_1}
- {OPERACAO_2}
- {OPERACAO_3}

Contexto de uso:
{CONTEXTO_DE_USO}
```

## Exemplo Preenchido

```
Implemente um repository para acesso ao serviço DynamoDB usando `boto3`.

Requisitos:
- Interface no `domain/repositories`
- Implementação concreta em `infrastructure/repositories`
- Tratamento de erros e logging com Datadog
- Tipagem completa usando type hints
- Retry com `tenacity` para operações falhas
- Teste unitário com `moto`

Operações necessárias:
- Salvar um pedido no DynamoDB
- Buscar um pedido por ID
- Atualizar o status de um pedido
- Listar pedidos por cliente_id com paginação

Contexto de uso:
O repositório será usado pelo caso de uso `ProcessarPedido` para persistir pedidos após validação.
A entidade de domínio é a seguinte:

```python
@dataclass
class Pedido:
    id: str
    cliente_id: str
    itens: List[Item]
    valor_total: float
    status: PedidoStatus = PedidoStatus.CRIADO
    data_criacao: datetime = field(default_factory=datetime.now)
```
```

## Como Adaptar

Para usar este template:

1. Substitua `{SERVICO_AWS}` pelo serviço AWS desejado (DynamoDB, SQS, SNS, S3, etc.)
2. Defina as `{OPERACAO_X}` com operações específicas que o gateway/repositório deve realizar
3. Forneça o `{CONTEXTO_DE_USO}` que explica como e onde o gateway será utilizado
4. Forneça qualquer entidade ou DTO relevante para o contexto

## Output Esperado

A IA deve gerar:

1. **Interface do gateway/repositório** - Contrato no domínio
```python
# domain/repositories/pedido_repository.py
class IPedidoRepository(Protocol):
    def salvar(self, pedido: Pedido) -> None: ...
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]: ...
    def atualizar_status(self, pedido_id: str, status: PedidoStatus) -> None: ...
    def listar_por_cliente(self, cliente_id: str, limit: int = 50, token: Optional[str] = None) -> Tuple[List[Pedido], Optional[str]]: ...
```

2. **Implementação concreta** - Lógica de acesso ao AWS na infraestrutura
```python
# infrastructure/repositories/dynamodb_pedido_repository.py
class DynamoDBPedidoRepository(IPedidoRepository):
    def __init__(self, dynamodb_client: Optional[Any] = None, table_name: str = "pedidos"):
        self.dynamodb = dynamodb_client or boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.logger = logging.getLogger(__name__)
        
    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
    )
    def salvar(self, pedido: Pedido) -> None:
        # Implementação...
```

3. **Classe de mapeamento** (se aplicável) - Para converter entre entidades e modelos de persistência
```python
# infrastructure/repositories/mappers/pedido_mapper.py
class PedidoMapper:
    @staticmethod
    def to_dynamo(pedido: Pedido) -> Dict[str, Any]:
        # Implementação...
        
    @staticmethod
    def from_dynamo(item: Dict[str, Any]) -> Pedido:
        # Implementação...
```

4. **Teste unitário** - Exemplo de como testar o gateway/repositório
```python
# tests/unit/infrastructure/repositories/test_dynamodb_pedido_repository.py
def test_salvar_pedido_sucesso():
    # Arrange
    with moto.mock_dynamodb():
        # Setup mock DynamoDB
        # ...
        
        # Act
        repo.salvar(pedido)
        
        # Assert
        # ...
```

## Boas Práticas para Gateways AWS

1. **Isolamento do Domínio**: Sua interface não deve expor tipos ou conceitos do AWS
2. **Imutabilidade**: Retorne cópias ou novos objetos, não modifique objetos recebidos
3. **Design Resiliente**: Implemente retries, circuit breakers e tratamento de erros robusto
4. **Logging Contextual**: Sempre log com contexto de operação e IDs relevantes
5. **Métricas**: Adicione métricas de latência, sucesso/falha e outros dados relevantes
6. **Paginação**: Para operações de lista, sempre implemente paginação adequada

## AWS SDK e Práticas Recomendadas

1. **Reutilização de Clientes**: Inicialize o cliente boto3 apenas uma vez e reutilize
2. **Batch Operations**: Use operações em lote quando possível para economizar chamadas
3. **Configuração por Ambiente**: Não hardcode configurações, use variáveis de ambiente ou SSM
4. **IAM**: Sugira políticas IAM com privilégios mínimos necessários
5. **Configuração de Timeout**: Ajuste os timeouts para refletir SLAs desejados 