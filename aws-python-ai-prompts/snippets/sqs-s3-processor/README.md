# Processador SQS-S3

Este snippet fornece uma abstração robusta para processar mensagens SQS que referenciam arquivos no S3, com suporte para deserialização em objetos Pydantic.

## Funcionalidades

- Consumo de mensagens SQS usando long-polling
- Download automático de arquivos referenciados no S3
- Deserialização de dados em objetos Pydantic
- Processamento em lote de múltiplas mensagens
- Confirmação e exclusão de mensagens processadas
- Tratamento de erros e retentativas
- Limpeza automática de arquivos temporários
- Suporte para integração com workflows existentes

## Código

O snippet é composto por três componentes principais:

1. Modelos de dados para mensagens SQS e referências S3
2. Um processador genérico que pode ser configurado com diferentes tipos de dados
3. Utilitários para tratar resultados e gerenciar arquivos temporários

### Exemplo Básico

```python
from pydantic import BaseModel
from sqs_s3_processor import SQSS3Processor

# Definir modelo de dados para deserialização
class ClienteData(BaseModel):
    id: str
    nome: str
    email: str
    idade: int = None
    endereco: str = None

# Criar o processador
processor = SQSS3Processor(
    queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/minha-fila",
    data_model=ClienteData
)

# Processar mensagens
results = processor.process_queue(auto_delete=True)

# Usar os dados processados
for result in results:
    if result.success:
        cliente = result.data
        print(f"Cliente processado: {cliente.nome} ({cliente.email})")
    else:
        print(f"Erro ao processar mensagem: {result.error}")
```

### Uso com Handler Personalizado

```python
def processar_cliente(result):
    """Handler personalizado para cada mensagem processada."""
    if not result.success:
        # Logar erro e retornar False para evitar excluir a mensagem
        print(f"Erro ao processar cliente: {result.error}")
        return False
        
    cliente = result.data
    
    # Fazer algum processamento adicional
    try:
        # Processar cliente...
        print(f"Cliente {cliente.id} processado com sucesso")
        return True  # OK para excluir a mensagem
    except Exception as e:
        print(f"Falha no processamento personalizado: {e}")
        return False  # Não excluir a mensagem devido a erro

# Usar o handler no processamento
processor.process_queue(handler=processar_cliente)
```

## Formatos de Mensagem Suportados

O processador tenta extrair referências S3 de vários formatos comuns de mensagens:

### Formato 1: Referência S3 Direta

```json
{
  "s3": {
    "bucket": "meu-bucket",
    "key": "caminho/para/arquivo.json",
    "versionId": "opcional-id-versao"
  },
  "metadata": {
    "sourceSystem": "sistema-origem",
    "timestamp": "2023-06-15T10:30:00Z"
  }
}
```

### Formato 2: Lista de Arquivos

```json
{
  "files": [
    {
      "bucket": "meu-bucket",
      "key": "caminho/para/arquivo1.json"
    },
    {
      "bucket": "meu-bucket",
      "key": "caminho/para/arquivo2.json"
    }
  ],
  "processId": "abc-123"
}
```

### Formato 3: Dados Inline com Referências S3

```json
{
  "data": {
    "id": "cliente-123",
    "nome": "Maria Silva"
  },
  "additionalFiles": [
    {
      "bucket": "meu-bucket",
      "key": "clientes/documentos/cliente-123.pdf"
    }
  ]
}
```

## Instalação

Para usar este snippet, adicione as seguintes dependências ao seu `requirements.txt`:

```
boto3>=1.26.0
pydantic>=1.10.0
```

## Configuração

### Variáveis de Ambiente

O processador utiliza as seguintes variáveis de ambiente opcionais:

```
# Região AWS (opcional, padrão é us-east-1)
AWS_REGION=us-east-1

# Limpeza automática de arquivos temporários (padrão é true)
AUTO_CLEANUP_TEMP_FILES=true

# Configuração de credenciais AWS (se não estiver usando perfis de instância)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## Customização

O processador foi projetado para ser facilmente customizável através de herança:

```python
class MeuProcessador(SQSS3Processor):
    """Processador customizado para necessidades específicas."""
    
    def extract_s3_references(self, message):
        """Sobrescrever para formatos de mensagem específicos."""
        # Implementação personalizada
        # ...
        
    def parse_data(self, message, downloaded_files):
        """Lógica personalizada de parsing."""
        # Implementação personalizada
        # ...
```

## Casos de Uso Comuns

### 1. Processador de Arquivos CSV do S3

```python
import pandas as pd
from sqs_s3_processor import SQSS3Processor, ProcessingResult

class CSVProcessor(SQSS3Processor):
    def parse_data(self, message, downloaded_files):
        # Ler CSV como DataFrame
        if not downloaded_files:
            raise ValueError("Nenhum arquivo CSV encontrado")
            
        df = pd.read_csv(downloaded_files[0])
        
        # Converter para objeto Pydantic
        records = df.to_dict('records')
        return [self.data_model(**record) for record in records]

# Uso
csv_processor = CSVProcessor(
    queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/csv-files",
    data_model=MeuModelo
)
```

### 2. Processador com DLQ (Dead Letter Queue)

```python
def handler_com_dlq(result, dlq_client, dlq_url):
    if not result.success:
        # Enviar para DLQ em caso de falha
        dlq_client.send_message(
            QueueUrl=dlq_url,
            MessageBody=json.dumps({
                "original_message_id": result.message_id,
                "error": str(result.error),
                "timestamp": datetime.now().isoformat()
            })
        )
        return True  # Podemos excluir a original, já que foi para DLQ
    return True
```

## Boas Práticas

1. **Tratamento de Erros:**
   - Sempre verifique `result.success` antes de usar os dados
   - Use `try/except` em código de manipulação de dados
   - Considere uma fila DLQ para mensagens que falham persistentemente

2. **Performance:**
   - Ajuste `max_messages` para otimizar o processamento em lote
   - Defina um `visibility_timeout` adequado para seu processamento
   - Use `wait_time_seconds=20` para long-polling eficiente

3. **Segurança:**
   - Use IAM Roles com permissões mínimas necessárias
   - Não armazene dados sensíveis no sistema de arquivos por muito tempo
   - Ative a criptografia em repouso para seus buckets S3 e filas SQS

4. **Observabilidade:**
   - Configure logging adequado para todas as operações
   - Implemente métricas para monitorar taxa de processamento e falhas
   - Ative o CloudWatch Logs para rastrear o processamento

## Limitações

- O processador baixa todos os arquivos referenciados antes de processá-los, o que pode consumir espaço temporário
- Não há suporte nativo para arquivos muito grandes (considere usar S3 Select para esses casos)
- O mecanismo de deserialização assume que os arquivos são JSON por padrão

## Recursos Adicionais

- [Documentação do AWS SQS](https://docs.aws.amazon.com/sqs/latest/developerguide/welcome.html)
- [Documentação do AWS S3](https://docs.aws.amazon.com/s3/latest/userguide/Welcome.html)
- [Documentação do Pydantic](https://pydantic-docs.helpmanual.io/) 