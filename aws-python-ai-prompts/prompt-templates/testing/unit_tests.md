# Testes Unitários para Aplicações AWS

Este prompt auxilia na criação de testes unitários eficazes para aplicações AWS Lambda e ECS seguindo Clean Architecture.

## Contexto para IA

```
Você irá criar testes unitários para componentes de uma aplicação AWS usando Python.
Os testes devem seguir boas práticas, ser independentes, rápidos e não dependerem 
de recursos reais da AWS. Use mocks, fixtures e ferramentas como pytest, moto e 
unittest.mock para criar testes eficazes.
```

## Prompt Base

```
Escreva testes unitários para o componente `{NOME_COMPONENTE}`.

Código do componente a ser testado:
```python
{CODIGO_COMPONENTE}
```

Dependências e interfaces que o componente utiliza:
```python
{DEPENDENCIAS_INTERFACES}
```

Requisitos dos testes:
- Use pytest como framework de testes
- Crie mocks para todas as dependências externas (incluindo serviços AWS)
- Teste cenários de sucesso e de erro
- Organize os testes por casos de uso/comportamentos
- Use fixtures quando apropriado para configuração
- Inclua testes para validar exceções e edge cases
- {REQUISITO_ADICIONAL}
```

## Exemplo Preenchido

```
Escreva testes unitários para o componente `ProcessarPedidoUseCase`.

Código do componente a ser testado:
```python
from domain.entities.pedido import Pedido, PedidoStatus
from domain.repositories import IPedidoRepository
from domain.gateways.notificacao import INotificacaoGateway
from application.dtos.pedido_dto import PedidoDTO, PedidoResponseDTO
from common.logging.interfaces import ILogger
from typing import Protocol, Optional
import uuid
from datadog import statsd

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
        try:
            self.logger.info(f"Processando pedido para cliente {pedido_dto.cliente_id}")
            
            # Inicia timer para métricas
            with statsd.timed('pedido.processamento.tempo', tags=[f'cliente:{pedido_dto.cliente_id}']):
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
                
                statsd.increment('pedido.processado', tags=[f'cliente:{pedido_dto.cliente_id}'])
                
            self.logger.info(f"Pedido {pedido.id} processado com sucesso")
            
            # Retorna DTO de resposta
            return PedidoResponseDTO(
                pedido_id=pedido.id,
                status=pedido.status.value,
                valor_total=float(total)
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao processar pedido: {str(e)}")
            statsd.increment('pedido.erro', tags=[f'erro:{type(e).__name__}'])
            raise
```

Dependências e interfaces que o componente utiliza:
```python
# domain/repositories.py
from typing import Protocol, Optional, List, Tuple
from domain.entities.pedido import Pedido, PedidoStatus

class IPedidoRepository(Protocol):
    def salvar(self, pedido: Pedido) -> None: ...
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]: ...
    def atualizar_status(self, pedido_id: str, status: PedidoStatus) -> None: ...
    
# domain/gateways/notificacao.py
from typing import Protocol

class INotificacaoGateway(Protocol):
    def enviar_notificacao(self, destinatario: str, mensagem: str) -> None: ...
    
# common/logging/interfaces.py
from typing import Protocol

class ILogger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str, exc_info=None) -> None: ...
    def warning(self, message: str) -> None: ...
    
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
```

Requisitos dos testes:
- Use pytest como framework de testes
- Crie mocks para todas as dependências externas (incluindo serviços AWS)
- Teste cenários de sucesso e de erro
- Organize os testes por casos de uso/comportamentos
- Use fixtures quando apropriado para configuração
- Inclua testes para validar exceções e edge cases
- Teste que as métricas Datadog são chamadas corretamente
```

## Como Adaptar

Para usar este template:

1. Substitua `{NOME_COMPONENTE}` pelo nome da classe ou função que deseja testar
2. Cole o código do componente em `{CODIGO_COMPONENTE}`
3. Cole as interfaces e classes de dependência em `{DEPENDENCIAS_INTERFACES}`
4. Adicione requisitos específicos em `{REQUISITO_ADICIONAL}`, se necessário

## Output Esperado

A IA deve gerar:

1. **Arquivo de teste completo** para o componente especificado. No exemplo acima, algo como:

```python
# tests/unit/application/usecases/test_processar_pedido_usecase.py
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from domain.entities.pedido import Pedido, PedidoStatus
from application.dtos.pedido_dto import PedidoDTO, ItemDTO, PedidoResponseDTO
from application.usecases.processar_pedido_usecase import ProcessarPedidoUseCase

@pytest.fixture
def mock_dependencies():
    """Fixture que cria todos os mocks necessários para os testes."""
    pedido_repo = Mock()
    notificacao_gateway = Mock()
    logger = Mock()
    
    return {
        "pedido_repo": pedido_repo,
        "notificacao_gateway": notificacao_gateway,
        "logger": logger
    }

@pytest.fixture
def sample_pedido_dto():
    """Fixture que cria um DTO de pedido para testes."""
    return PedidoDTO(
        cliente_id="cliente123",
        itens=[
            ItemDTO(
                produto_id="prod1",
                quantidade=2,
                preco_unitario=50.0
            )
        ]
    )

@pytest.fixture
def use_case(mock_dependencies):
    """Fixture que cria a instância do caso de uso."""
    return ProcessarPedidoUseCase(
        pedido_repo=mock_dependencies["pedido_repo"],
        notificacao_gateway=mock_dependencies["notificacao_gateway"],
        logger=mock_dependencies["logger"]
    )

class TestProcessarPedidoUseCase:
    def test_processar_pedido_sucesso(self, use_case, mock_dependencies, sample_pedido_dto):
        # Arrange
        mock_pedido = Mock(spec=Pedido)
        mock_pedido.id = "pedido123"
        mock_pedido.status = PedidoStatus.PROCESSADO
        mock_pedido.calcular_total.return_value = Decimal("100.00")
        
        # Mock para a criação do Pedido a partir do DTO
        with patch("domain.entities.pedido.Pedido.from_dict", return_value=mock_pedido):
            # Act
            result = use_case.execute(sample_pedido_dto)
            
            # Assert
            assert isinstance(result, PedidoResponseDTO)
            assert result.pedido_id == "pedido123"
            assert result.status == PedidoStatus.PROCESSADO.value
            assert result.valor_total == 100.00
            
            # Verificar que os métodos foram chamados corretamente
            mock_dependencies["pedido_repo"].salvar.assert_called_once_with(mock_pedido)
            mock_pedido.marcar_como_processado.assert_called_once()
            mock_dependencies["pedido_repo"].atualizar_status.assert_called_once_with(
                mock_pedido.id, mock_pedido.status
            )
            mock_dependencies["notificacao_gateway"].enviar_notificacao.assert_called_once()
            mock_dependencies["logger"].info.assert_called()
    
    def test_erro_ao_processar_pedido(self, use_case, mock_dependencies, sample_pedido_dto):
        # Arrange
        mock_dependencies["pedido_repo"].salvar.side_effect = Exception("Erro ao salvar")
        
        # Act & Assert
        with pytest.raises(Exception):
            use_case.execute(sample_pedido_dto)
            
        # Verificar que o logger foi chamado com error
        mock_dependencies["logger"].error.assert_called()
    
    @patch("datadog.statsd.increment")
    @patch("datadog.statsd.timed")
    def test_datadog_metricas(self, mock_timed, mock_increment, use_case, 
                             mock_dependencies, sample_pedido_dto):
        # Arrange
        mock_timed.return_value.__enter__.return_value = None
        mock_timed.return_value.__exit__.return_value = None
        
        mock_pedido = Mock(spec=Pedido)
        mock_pedido.id = "pedido123"
        mock_pedido.status = PedidoStatus.PROCESSADO
        mock_pedido.calcular_total.return_value = Decimal("100.00")
        
        # Act
        with patch("domain.entities.pedido.Pedido.from_dict", return_value=mock_pedido):
            use_case.execute(sample_pedido_dto)
        
        # Assert
        mock_timed.assert_called_once()
        mock_increment.assert_called_with(
            'pedido.processado', 
            tags=[f'cliente:{sample_pedido_dto.cliente_id}']
        )
```

## Boas Práticas para Testes Unitários

1. **Isolamento**: Cada teste deve ser independente dos outros
2. **Mocks**: Use mocks para substituir dependências externas
3. **Arrange-Act-Assert**: Estruture seus testes neste padrão
4. **Fixtures**: Use fixtures para código de configuração reutilizável
5. **Coverage**: Busque boa cobertura de testes, mas priorize qualidade sobre quantidade
6. **Naming**: Use nomes descritivos que expliquem o comportamento testado
7. **Parametrização**: Use `@pytest.mark.parametrize` para testar múltiplos casos
8. **Não teste a implementação**: Teste o comportamento, não os detalhes de implementação

## Ferramentas Úteis para Teste em AWS

1. **moto**: Mock de serviços AWS (DynamoDB, S3, SQS, etc.)

```python
import boto3
import pytest
from moto import mock_dynamodb

@pytest.fixture
def dynamodb_table():
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='pedidos',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
        )
        yield table
```

2. **unittest.mock.patch**: Para patch de funções e métodos

```python
@patch('boto3.client')
def test_something(mock_boto_client):
    mock_boto_client.return_value.get_item.return_value = {'Item': {...}}
```

3. **freezegun**: Para controlar datas em testes

```python
from freezegun import freeze_time

@freeze_time("2023-01-01")
def test_with_fixed_date():
    # datetime.now() retornará 2023-01-01
``` 