# Cliente HTTP com Deserialização Automática

Este snippet fornece uma abstração robusta para fazer chamadas HTTP e deserializar automaticamente as respostas JSON em DTOs (Data Transfer Objects) usando Pydantic.

## Funcionalidades

- Cliente HTTP completo com suporte a todos os métodos (GET, POST, PUT, DELETE, etc.)
- Deserialização automática de respostas JSON para objetos Pydantic
- Tratamento abrangente de erros e exceções
- Configuração flexível (timeouts, retries, SSL, etc.)
- Suporte a autenticação
- Logging estruturado
- Métricas de performance (tempos de resposta)
- Gerenciamento automatizado de sessões

## Código

O cliente HTTP é composto por:

1. Uma classe principal `HttpClient` para fazer requisições
2. Uma classe `HttpResponse` que encapsula respostas com dados já deserializados
3. Configurações personalizáveis via `HttpClientConfig`

### Exemplo Básico

```python
from pydantic import BaseModel
from http_client import HttpClient

# Definir modelo para os dados de resposta
class Usuario(BaseModel):
    id: int
    nome: str
    email: str
    pontos: int = 0

# Criar cliente HTTP
client = HttpClient(
    config=HttpClientConfig(
        base_url="https://api.example.com/v1"
    )
)

# Fazer uma requisição GET e deserializar a resposta
response = client.get("usuarios/123", response_model=Usuario)

if response.success:
    usuario = response.data
    print(f"Usuário: {usuario.nome} (Email: {usuario.email})")
else:
    print(f"Erro: {response.error_message}")
```

### Enviando dados em POST/PUT

```python
# Definir modelo para os dados de requisição
class CriarUsuario(BaseModel):
    nome: str
    email: str
    senha: str

# Definir modelo para a resposta
class UsuarioCriado(BaseModel):
    id: int
    nome: str
    email: str
    criado_em: str

# Criar dados com validação
dados_usuario = CriarUsuario(
    nome="João Silva",
    email="joao@example.com",
    senha="senha123"
)

# Enviar requisição POST com dados
response = client.post(
    "usuarios", 
    data=dados_usuario,  # Pode ser dict ou Pydantic model
    response_model=UsuarioCriado
)

if response.success:
    usuario = response.data
    print(f"Usuário criado com ID: {usuario.id}")
else:
    print(f"Erro ao criar usuário: {response.error_message}")
```

## Instalação

Adicione as seguintes dependências ao seu `requirements.txt`:

```
requests>=2.28.0
pydantic>=1.10.0
urllib3>=1.26.0
```

## Configuração

O cliente HTTP pode ser configurado com diversos parâmetros:

```python
from http_client import HttpClient, HttpClientConfig

client = HttpClient(
    config=HttpClientConfig(
        base_url="https://api.example.com",
        timeout=30,                     # Timeout em segundos
        verify_ssl=True,                # Verificar certificados SSL
        max_retries=3,                  # Máximo de retentativas
        retry_backoff_factor=0.5,       # Fator para exponential backoff
        retry_on_status=[500, 502, 503, 504],  # Códigos para retry
        auth=("username", "password"),  # Auth básica (opcional)
        log_request_body=False,         # Logar corpo das requisições
        log_response_body=False,        # Logar corpo das respostas
        default_headers={               # Cabeçalhos padrão
            "User-Agent": "MyApp/1.0",
            "X-Custom-Header": "valor"
        }
    )
)
```

## Casos de Uso Avançados

### 1. Autenticação OAuth

```python
# Exemplo com token OAuth
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1..."

client = HttpClient(
    config=HttpClientConfig(
        base_url="https://api.segura.com/v2",
        default_headers={
            "Authorization": f"Bearer {token}"
        }
    )
)
```

### 2. Upload de Arquivo

```python
# Upload de arquivo
with open("documento.pdf", "rb") as file:
    response = client.post(
        "documentos/upload",
        data=file,
        headers={"Content-Type": "application/pdf"}
    )
```

### 3. Tratamento de Erro Personalizado

```python
# Função personalizada para extrair mensagens de erro
def extrair_erro_api(response):
    try:
        json_data = response.json()
        return json_data.get("errors", {}).get("message", "Erro desconhecido")
    except:
        return "Erro ao processar resposta"

# Usar handler personalizado
response = client.get(
    "recursos/123", 
    error_handler=extrair_erro_api
)
```

### 4. Processamento de Listas

```python
from typing import List

# Modelo para lista de itens
class Item(BaseModel):
    id: int
    nome: str
    preco: float

# Receber lista de itens
response = client.get(
    "produtos/categoria/eletronicos",
    response_model=List[Item]  # Deserializar lista de objetos
)

if response.success:
    itens = response.data
    for item in itens:
        print(f"Produto: {item.nome} - R$ {item.preco:.2f}")
```

## Boas Práticas

1. **Gerenciamento de Recursos**
   - Use o cliente com contexto (`with`) para garantir que a sessão seja fechada
   ```python
   with HttpClient(config) as client:
       response = client.get("endpoint")
   # Sessão fechada automaticamente ao sair do contexto
   ```

2. **Verificação de Sucesso**
   - Sempre verifique `response.success` antes de acessar `response.data`
   ```python
   if response.success:
       # Usar response.data
   else:
       # Tratar response.error_message
   ```

3. **Timeout Adequado**
   - Configure timeouts adequados para cada endpoint
   ```python
   # Endpoint que pode demorar mais
   client.get("relatorios/grande", timeout=120)
   ```

4. **Logs para Depuração**
   - Ative logs detalhados durante desenvolvimento/troubleshooting
   ```python
   debug_config = HttpClientConfig(
       log_request_body=True,
       log_response_body=True
   )
   ```

## Extensão e Personalização

O cliente pode ser estendido para casos de uso específicos:

```python
class MeuClienteAPI(HttpClient):
    """Cliente personalizado para API específica."""
    
    def __init__(self, api_key: str):
        config = HttpClientConfig(
            base_url="https://minha-api.com/v1",
            default_headers={"X-API-Key": api_key}
        )
        super().__init__(config)
    
    def listar_usuarios(self):
        """Endpoint específico para listar usuários."""
        return self.get("usuarios", response_model=List[Usuario])
    
    def criar_usuario(self, nome: str, email: str):
        """Endpoint para criar usuário."""
        return self.post(
            "usuarios",
            data={"nome": nome, "email": email},
            response_model=Usuario
        )
```

## Limitações

- Não suporta nativamente streaming de resposta
- A deserialização assume que a resposta é JSON (embora suporte respostas não-JSON)
- Para APIs com estruturas de resposta complexas ou inconsistentes, pode ser necessário personalizar o parsing

## Recursos Adicionais

- [Documentação do Requests](https://docs.python-requests.org/)
- [Documentação do Pydantic](https://pydantic-docs.helpmanual.io/)
- [Melhores práticas para clientes HTTP resilientes](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) 