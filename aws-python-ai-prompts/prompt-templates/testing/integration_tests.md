# Testes de Integração para Aplicações AWS

Este prompt auxilia na criação de testes de integração para aplicações AWS Lambda e ECS, incluindo mocks de serviços AWS com bibliotecas como `moto`.

## Contexto para IA

```
Você irá criar testes de integração para uma aplicação AWS usando Python.
Os testes de integração verificam como múltiplos componentes interagem entre si,
mas sem depender de recursos reais da AWS em ambiente de teste. Você usará
ferramentas como moto para mockear serviços AWS e pytest para estruturar os testes.
```

## Prompt Base

```
Escreva testes de integração para verificar a interação entre `{COMPONENTE_PRIMARIO}` e `{COMPONENTE_SECUNDARIO}` usando serviços AWS.

Componentes a serem testados:
```python
{CODIGO_COMPONENTES}
```

Contexto e dependências:
```python
{CONTEXTO_DEPENDENCIAS}
```

Requisitos dos testes:
- Use pytest como framework de testes
- Crie mocks de serviços AWS usando moto ({SERVICOS_AWS})
- Configure o ambiente necessário antes dos testes
- Teste fluxos de integração completos
- Verifique o estado final após a execução
- Limpe recursos criados durante os testes
- {REQUISITO_ADICIONAL}

Serviços AWS a serem mockados: {SERVICOS_AWS}
```

## Exemplo Preenchido

```
Escreva testes de integração para verificar a interação entre `ProcessarPedidoUseCase` e `DynamoDBPedidoRepository` usando serviços AWS.

Componentes a serem testados:
```python
# application/usecases/processar_pedido_usecase.py
from domain.entities.pedido import Pedido
from domain.repositories import IPedidoRepository
from domain.gateways.notificacao import INotificacaoGateway
from application.dtos.pedido_dto import PedidoDTO, PedidoResponseDTO
from common.logging.interfaces import ILogger

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

# infrastructure/database/repositories/dynamodb_pedido_repository.py
import boto3
from botocore.exceptions import ClientError
from typing import Optional, List, Tuple, Dict, Any
from decimal import Decimal
from domain.entities.pedido import Pedido, PedidoStatus
from domain.repositories import IPedidoRepository
from infrastructure.database.mappers.pedido_mapper import PedidoMapper
from common.logging.interfaces import ILogger

class DynamoDBPedidoRepository(IPedidoRepository):
    def __init__(
        self, 
        logger: ILogger,
        table_name: str = "pedidos",
        dynamodb_resource = None
    ):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.logger = logger
        
    def salvar(self, pedido: Pedido) -> None:
        try:
            item = PedidoMapper.to_dynamo(pedido)
            self.table.put_item(Item=item)
            self.logger.info(f"Pedido {pedido.id} salvo com sucesso")
        except ClientError as e:
            self.logger.error(f"Erro ao salvar pedido {pedido.id}: {str(e)}")
            raise
            
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        try:
            response = self.table.get_item(Key={"id": pedido_id})
            if "Item" not in response:
                return None
                
            return PedidoMapper.from_dynamo(response["Item"])
        except ClientError as e:
            self.logger.error(f"Erro ao buscar pedido {pedido_id}: {str(e)}")
            raise
            
    def atualizar_status(self, pedido_id: str, status: PedidoStatus) -> None:
        try:
            self.table.update_item(
                Key={"id": pedido_id},
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": status.value}
            )
            self.logger.info(f"Status do pedido {pedido_id} atualizado para {status}")
        except ClientError as e:
            self.logger.error(f"Erro ao atualizar status do pedido {pedido_id}: {str(e)}")
            raise
```

Contexto e dependências:
```python
# domain/entities/pedido.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from enum import Enum

class PedidoStatus(str, Enum):
    CRIADO = "CRIADO"
    PROCESSANDO = "PROCESSANDO"
    PROCESSADO = "PROCESSADO"
    CANCELADO = "CANCELADO"
    ERRO = "ERRO"

class Item(BaseModel):
    produto_id: str
    quantidade: int
    preco_unitario: Decimal
    desconto: Optional[Decimal] = Field(default=Decimal('0.00'))
    
    def subtotal(self) -> Decimal:
        return (self.preco_unitario * self.quantidade) - self.desconto

class Pedido(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    cliente_id: str
    itens: List[Item]
    valor_total: Optional[Decimal] = None
    status: PedidoStatus = Field(default=PedidoStatus.CRIADO)
    data_criacao: datetime = Field(default_factory=datetime.now)
    
    def calcular_total(self) -> Decimal:
        self.valor_total = sum(item.subtotal() for item in self.itens)
        return self.valor_total
        
    def marcar_como_processado(self) -> None:
        self.status = PedidoStatus.PROCESSADO
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pedido':
        if 'itens' in data and isinstance(data['itens'], list):
            data['itens'] = [Item(**item) for item in data['itens']]
        
        pedido = cls(**data)
        if not pedido.valor_total:
            pedido.calcular_total()
            
        return pedido

# infrastructure/database/mappers/pedido_mapper.py
from typing import Dict, Any
from decimal import Decimal
import json
from domain.entities.pedido import Pedido, Item, PedidoStatus
from datetime import datetime

class PedidoMapper:
    @staticmethod
    def to_dynamo(pedido: Pedido) -> Dict[str, Any]:
        return {
            "id": pedido.id,
            "cliente_id": pedido.cliente_id,
            "itens": [
                {
                    "produto_id": item.produto_id,
                    "quantidade": item.quantidade,
                    "preco_unitario": item.preco_unitario,
                    "desconto": item.desconto
                }
                for item in pedido.itens
            ],
            "valor_total": pedido.valor_total,
            "status": pedido.status.value,
            "data_criacao": pedido.data_criacao.isoformat()
        }
        
    @staticmethod
    def from_dynamo(item: Dict[str, Any]) -> Pedido:
        # Converte strings para Decimal para campos numéricos
        for i in item.get("itens", []):
            i["preco_unitario"] = Decimal(str(i["preco_unitario"]))
            i["desconto"] = Decimal(str(i.get("desconto", "0")))
            
        valor_total = Decimal(str(item.get("valor_total", "0")))
        
        return Pedido(
            id=item["id"],
            cliente_id=item["cliente_id"],
            itens=[Item(**i) for i in item["itens"]],
            valor_total=valor_total,
            status=PedidoStatus(item["status"]),
            data_criacao=datetime.fromisoformat(item["data_criacao"])
        )

# application/dtos/pedido_dto.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ItemDTO(BaseModel):
    produto_id: str
    quantidade: int
    preco_unitario: float
    desconto: Optional[float] = 0.0

class PedidoDTO(BaseModel):
    cliente_id: str
    itens: List[ItemDTO]
    
class PedidoResponseDTO(BaseModel):
    pedido_id: str
    status: str
    valor_total: float
    
# domain/gateways/notificacao.py
from typing import Protocol

class INotificacaoGateway(Protocol):
    def enviar_notificacao(self, destinatario: str, mensagem: str) -> None: ...

# common/logging/interfaces.py
from typing import Protocol, Optional

class ILogger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str, exc_info: Optional[Exception] = None) -> None: ...
    def warning(self, message: str) -> None: ...
```

Requisitos dos testes:
- Use pytest como framework de testes
- Crie mocks de serviços AWS usando moto (DynamoDB)
- Configure o ambiente necessário antes dos testes
- Teste fluxos de integração completos
- Verifique o estado final após a execução
- Limpe recursos criados durante os testes
- Assegure que os dados são corretamente armazenados e recuperados do DynamoDB

Serviços AWS a serem mockados: DynamoDB
```

## Como Adaptar

Para usar este template:

1. Substitua `{COMPONENTE_PRIMARIO}` e `{COMPONENTE_SECUNDARIO}` pelos componentes que deseja testar
2. Insira o código dos componentes em `{CODIGO_COMPONENTES}`
3. Inclua o contexto e dependências em `{CONTEXTO_DEPENDENCIAS}`
4. Liste os serviços AWS a serem mockados em `{SERVICOS_AWS}`
5. Adicione requisitos específicos em `{REQUISITO_ADICIONAL}`, se necessário

## Output Esperado

A IA deve gerar:

1. **Arquivo de teste de integração completo**, por exemplo:

```python
# tests/integration/test_pedido_integration.py
import pytest
import boto3
from moto import mock_dynamodb
from unittest.mock import Mock
from datetime import datetime
from decimal import Decimal

from domain.entities.pedido import Pedido, PedidoStatus
from application.dtos.pedido_dto import PedidoDTO, ItemDTO
from application.usecases.processar_pedido_usecase import ProcessarPedidoUseCase
from infrastructure.database.repositories.dynamodb_pedido_repository import DynamoDBPedidoRepository

@pytest.fixture
def mock_logger():
    logger = Mock()
    return logger

@pytest.fixture
def mock_notificacao_gateway():
    gateway = Mock()
    return gateway

@pytest.fixture
def dynamodb_pedidos_table():
    with mock_dynamodb():
        # Criar cliente DynamoDB e tabela
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Criar tabela
        table = dynamodb.create_table(
            TableName='pedidos',
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        yield dynamodb, table

@pytest.fixture
def pedido_repository(dynamodb_pedidos_table, mock_logger):
    dynamodb, _ = dynamodb_pedidos_table
    return DynamoDBPedidoRepository(
        logger=mock_logger,
        table_name='pedidos',
        dynamodb_resource=dynamodb
    )

@pytest.fixture
def use_case(pedido_repository, mock_notificacao_gateway, mock_logger):
    return ProcessarPedidoUseCase(
        pedido_repo=pedido_repository,
        notificacao_gateway=mock_notificacao_gateway,
        logger=mock_logger
    )

@pytest.fixture
def sample_pedido_dto():
    return PedidoDTO(
        cliente_id="cliente123",
        itens=[
            ItemDTO(
                produto_id="prod1",
                quantidade=2,
                preco_unitario=50.0
            ),
            ItemDTO(
                produto_id="prod2",
                quantidade=1,
                preco_unitario=30.0,
                desconto=5.0
            )
        ]
    )

class TestPedidoIntegration:
    def test_processar_pedido_e_salvar_no_dynamodb(
        self, use_case, pedido_repository, mock_notificacao_gateway, 
        sample_pedido_dto, dynamodb_pedidos_table
    ):
        # Act: Executar o caso de uso
        result = use_case.execute(sample_pedido_dto)
        
        # Assert: Verificar a resposta
        assert result.pedido_id is not None
        assert result.status == PedidoStatus.PROCESSADO.value
        assert result.valor_total == 125.0  # (50*2) + (30-5)
        
        # Assert: Verificar a notificação
        mock_notificacao_gateway.enviar_notificacao.assert_called_once()
        
        # Assert: Verificar que o pedido foi salvo no DynamoDB
        pedido_salvo = pedido_repository.buscar_por_id(result.pedido_id)
        assert pedido_salvo is not None
        assert pedido_salvo.cliente_id == sample_pedido_dto.cliente_id
        assert pedido_salvo.status == PedidoStatus.PROCESSADO
        assert pedido_salvo.valor_total == Decimal('125.0')
        assert len(pedido_salvo.itens) == 2
        
    def test_processar_pedido_atualizar_status(
        self, use_case, pedido_repository, sample_pedido_dto
    ):
        # Act: Executar o caso de uso
        result = use_case.execute(sample_pedido_dto)
        
        # Verificar status inicial
        pedido = pedido_repository.buscar_por_id(result.pedido_id)
        assert pedido.status == PedidoStatus.PROCESSADO
        
        # Atualizar status manualmente
        pedido_repository.atualizar_status(result.pedido_id, PedidoStatus.CANCELADO)
        
        # Verificar que o status foi atualizado
        pedido_atualizado = pedido_repository.buscar_por_id(result.pedido_id)
        assert pedido_atualizado.status == PedidoStatus.CANCELADO
```

## Boas Práticas para Testes de Integração

1. **Isole os Recursos**: Use moto para isolar seus testes de recursos AWS reais
2. **Setup/Teardown**: Configure o ambiente antes dos testes e limpe depois
3. **Fluxos Completos**: Teste fluxos de ponta a ponta, não apenas componentes isolados
4. **Verifique Estado Final**: Cheque se o sistema chegou ao estado esperado
5. **Tags Específicas**: Use `pytest.mark.integration` para marcar testes de integração
6. **Mock Seletivo**: Mock apenas o que não é parte da integração sendo testada
7. **Evite Acoplamento**: Os testes não devem depender da ordem de execução

## Recursos Específicos por Serviço AWS

### DynamoDB com Moto

```python
@pytest.fixture
def dynamodb_table():
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='minha_tabela',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        yield table
```

### S3 com Moto

```python
@pytest.fixture
def s3_bucket():
    with mock_s3():
        s3 = boto3.resource('s3', region_name='us-east-1')
        bucket = s3.create_bucket(Bucket='test-bucket')
        yield bucket
```

### SQS com Moto

```python
@pytest.fixture
def sqs_queue():
    with mock_sqs():
        sqs = boto3.resource('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName='test-queue')
        yield queue
```

### Lambda com Moto

```python
@pytest.fixture
def lambda_function():
    with mock_lambda():
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        lambda_client.create_function(
            FunctionName='test-function',
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/lambda-role',
            Handler='index.handler',
            Code={'ZipFile': b'bytes'},
            Timeout=30
        )
        yield lambda_client
``` 