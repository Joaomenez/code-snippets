# Implementação de Caso de Uso

Este prompt auxilia na criação de casos de uso seguindo Clean Architecture para aplicações AWS Lambda e ECS.

## Contexto para IA

```
Você irá implementar um caso de uso seguindo Clean Architecture. 
O caso de uso deve ser independente de frameworks e detalhes de infraestrutura, 
seguir o princípio de inversão de dependência, e ser facilmente testável.
```

## Prompt Base

```
Implemente o caso de uso chamado `{NOME_CASO_USO}`.

Responsabilidades:
- Receber {ENTRADA_CASO_USO}
- {RESPONSABILIDADE_1}
- {RESPONSABILIDADE_2}
- {RESPONSABILIDADE_3}
- {RESPONSABILIDADE_4}
- {RESPONSABILIDADE_5}

Siga Clean Architecture:
- Interface no `application/use_cases`
- Implementação separada
- Dependa apenas de abstrações (não use boto3 diretamente)
- Logs e métricas com Datadog
- Inclua teste unitário

Use as seguintes entidades de domínio e repositórios:
{ENTIDADES_E_REPOS}

Estrutura esperada:
1. Interface do caso de uso
2. Implementação do caso de uso
3. Exemplo de teste unitário
```

## Exemplo Preenchido

```
Implemente o caso de uso chamado `ProcessarPedido`.

Responsabilidades:
- Receber um objeto PedidoDTO
- Validar os dados do pedido
- Calcular o valor total do pedido
- Persistir o pedido no repositório
- Marcar o pedido como processado
- Notificar sucesso via gateway de notificação

Siga Clean Architecture:
- Interface no `application/use_cases`
- Implementação separada
- Dependa apenas de abstrações (não use boto3 diretamente)
- Logs e métricas com Datadog
- Inclua teste unitário

Use as seguintes entidades de domínio e repositórios:
```python
# domain/entities/pedido.py
@dataclass
class Pedido:
    id: str
    cliente_id: str
    itens: List[Item]
    valor_total: float
    status: PedidoStatus
    
    def marcar_como_processado(self) -> None:
        self.status = PedidoStatus.PROCESSADO

# domain/repositories.py
class IPedidoRepository(Protocol):
    def salvar(self, pedido: Pedido) -> None: ...
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]: ...

# domain/gateways/notificacao.py
class INotificacaoGateway(Protocol):
    def enviar_notificacao(self, destinatario: str, mensagem: str) -> None: ...
```

Estrutura esperada:
1. Interface do caso de uso
2. Implementação do caso de uso
3. Exemplo de teste unitário
```

## Como Adaptar

Para usar este template:

1. Substitua `{NOME_CASO_USO}` pelo nome do seu caso de uso (ex: ProcessarPedido, AutenticarUsuario)
2. Substitua `{ENTRADA_CASO_USO}` pela entrada do caso de uso (ex: objeto PedidoDTO, credenciais)
3. Defina as `{RESPONSABILIDADE_X}` com ações específicas que o caso de uso deve realizar
4. Forneça as entidades e interfaces de repositório em `{ENTIDADES_E_REPOS}`

## Output Esperado

A IA deve gerar:

1. **Interface do caso de uso** - Contrato que define a operação
```python
# application/use_cases/processar_pedido.py
class IProcessarPedidoUseCase(Protocol):
    def execute(self, pedido_dto: PedidoDTO) -> PedidoResponseDTO: ...
```

2. **Implementação do caso de uso** - Lógica concreta que implementa a interface
```python
# application/use_cases/processar_pedido_impl.py
class ProcessarPedidoUseCase(IProcessarPedidoUseCase):
    def __init__(self, pedido_repo: IPedidoRepository, notificacao: INotificacaoGateway):
        self.pedido_repo = pedido_repo
        self.notificacao = notificacao
        
    def execute(self, pedido_dto: PedidoDTO) -> PedidoResponseDTO:
        # Implementação...
```

3. **Teste unitário** - Exemplo de como testar o caso de uso
```python
# tests/unit/application/use_cases/test_processar_pedido.py
def test_processar_pedido_sucesso():
    # Arrange
    pedido_repo_mock = Mock(spec=IPedidoRepository)
    notificacao_mock = Mock(spec=INotificacaoGateway)
    # ...
```

## Alinhamento com Clean Architecture

- O caso de uso deve depender apenas de interfaces/abstrações
- Toda lógica de negócio deve ser executada pelo domínio, não pelo caso de uso
- O caso de uso é apenas um orquestrador que coordena operações
- Dependências externas são injetadas via construtor 