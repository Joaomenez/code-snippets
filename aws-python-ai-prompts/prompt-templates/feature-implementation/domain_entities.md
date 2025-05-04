# Definição de Entidades de Domínio

Este prompt auxilia na criação de entidades de domínio usando `pydantic` para aplicações AWS Lambda e ECS.

## Contexto para IA

```
Você irá modelar entidades de domínio usando Pydantic, aplicando tipagem forte, validações
e boas práticas. As entidades são o núcleo do domínio e devem encapsular regras de negócio
e invariantes, sendo independentes de frameworks e detalhes de implementação.
```

## Prompt Base

```
A partir do seguinte caso de uso, infira e modele as entidades de domínio com `pydantic`, usando tipagem forte, validações e boas práticas.

Caso de uso:
"{DESCRICAO_CASO_USO}"

Requisitos:
- Crie entidades como {LISTA_ENTIDADES}
- Separe em arquivos distintos
- Use métodos auxiliares como `.from_dict()`
- Adicione validações e enums se necessário
- Implemente métodos de negócio nas entidades
- Use dataclasses de Pydantic e type hints
```

## Exemplo Preenchido

```
A partir do seguinte caso de uso, infira e modele as entidades de domínio com `pydantic`, usando tipagem forte, validações e boas práticas.

Caso de uso:
"Processar pedidos recebidos via fila SQS. O pedido contém id, cliente, lista de itens, e total. Deve ser validado, persistido e marcado como processado."

Requisitos:
- Crie entidades como `Pedido`, `Cliente`, `Item`, `PedidoStatus`
- Separe em arquivos distintos
- Use métodos auxiliares como `.from_dict()`
- Adicione validações e enums se necessário
- Implemente métodos de negócio nas entidades
- Use dataclasses de Pydantic e type hints
```

## Como Adaptar

Para usar este template:

1. Substitua `{DESCRICAO_CASO_USO}` pela descrição do seu caso de uso específico
2. Substitua `{LISTA_ENTIDADES}` por uma lista sugerida de entidades a serem criadas

## Output Esperado

A IA deve gerar:

1. **Entidades de domínio** em arquivos separados. Exemplo para o caso de uso de Pedidos:

```python
# domain/entities/pedido_status.py
from enum import Enum, auto

class PedidoStatus(str, Enum):
    CRIADO = "CRIADO"
    PROCESSANDO = "PROCESSANDO"
    PROCESSADO = "PROCESSADO"
    CANCELADO = "CANCELADO"
    ERRO = "ERRO"
```

```python
# domain/entities/item.py
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from typing import Optional

class Item(BaseModel):
    produto_id: str
    quantidade: int
    preco_unitario: Decimal
    desconto: Optional[Decimal] = Field(default=Decimal('0.00'))
    
    @validator('quantidade')
    def quantidade_deve_ser_positiva(cls, v):
        if v <= 0:
            raise ValueError('Quantidade deve ser maior que zero')
        return v
        
    @validator('preco_unitario', 'desconto')
    def preco_deve_ser_positivo(cls, v):
        if v < Decimal('0.00'):
            raise ValueError('Valores monetários não podem ser negativos')
        return v
        
    def subtotal(self) -> Decimal:
        return (self.preco_unitario * self.quantidade) - self.desconto
```

```python
# domain/entities/pedido.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from decimal import Decimal

from .pedido_status import PedidoStatus
from .item import Item

class Pedido(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    cliente_id: str
    itens: List[Item]
    valor_total: Optional[Decimal] = None
    status: PedidoStatus = Field(default=PedidoStatus.CRIADO)
    data_criacao: datetime = Field(default_factory=datetime.now)
    
    @validator('itens')
    def pedido_deve_ter_itens(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Pedido deve ter pelo menos um item')
        return v
        
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
```

2. **Validações Relevantes** para garantir a integridade das entidades

3. **Métodos de Negócio** encapsulados nas próprias entidades

## Boas Práticas para Entidades de Domínio

1. **Imutabilidade**: Use frozen=True quando possível para entidades que não devem mudar
2. **Validação**: Use validators do Pydantic para validar invariantes
3. **Encapsulamento**: Coloque comportamentos relevantes dentro da entidade
4. **Tell, Don't Ask**: Prefira métodos que executam ações ao invés de getters/setters
5. **Value Objects**: Use objetos de valor para conceitos imutáveis (ex: CPF, Email, Endereço)
6. **Separação**: Uma entidade por arquivo para manter o código organizado
7. **Type Hints**: Use tipagem forte para melhorar a documentação e IDE support 