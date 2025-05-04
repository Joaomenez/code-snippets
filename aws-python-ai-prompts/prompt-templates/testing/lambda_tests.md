# Testes de Funções AWS Lambda

Este prompt auxilia na criação de testes para funções AWS Lambda, incluindo mocks de eventos, context e serviços AWS.

## Contexto para IA

```
Você irá criar testes unitários e de integração para uma função AWS Lambda em Python.
Os testes devem verificar o comportamento da função com diferentes eventos de entrada,
usando mocks apropriados para serviços AWS e respeitando as melhores práticas de teste.
```

## Prompt Base

```
Crie testes para uma função AWS Lambda em Python que {DESCRICAO_FUNCIONALIDADE}.

Código da função Lambda:
```python
{CODIGO_LAMBDA}
```

Requisitos dos testes:
- Utilize pytest como framework de testes
- Mocke serviços AWS com moto para {SERVICOS_AWS}
- Teste cenários de sucesso e falha
- Verifique o tratamento correto de exceções
- {REQUISITO_ADICIONAL}

A função Lambda é acionada por {TIPO_TRIGGER} e realiza {ACAO_PRINCIPAL}.
```

## Exemplo Preenchido

```
Crie testes para uma função AWS Lambda em Python que processa mensagens SQS e salva dados no DynamoDB.

Código da função Lambda:
```python
# lambda_function.py
import json
import os
import boto3
import logging
from datetime import datetime
import uuid
from botocore.exceptions import ClientError

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar recursos AWS
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('ORDERS_TABLE', 'orders'))

def lambda_handler(event, context):
    """
    Processa mensagens SQS contendo pedidos e salva no DynamoDB.
    """
    processed_orders = 0
    failed_orders = 0
    
    try:
        # Processar mensagens SQS
        for record in event.get('Records', []):
            try:
                # Extrair corpo da mensagem
                message_body = json.loads(record.get('body', '{}'))
                
                # Validar dados mínimos
                if not all(k in message_body for k in ['customer_id', 'items']):
                    logger.error(f"Invalid order data: missing required fields")
                    failed_orders += 1
                    continue
                
                # Gerar ID e data
                order_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                # Calcular total
                total = sum(item.get('price', 0) * item.get('quantity', 0) 
                           for item in message_body.get('items', []))
                
                # Criar item para salvar
                order_item = {
                    'id': order_id,
                    'customer_id': message_body['customer_id'],
                    'items': message_body['items'],
                    'total': total,
                    'status': 'RECEIVED',
                    'created_at': timestamp
                }
                
                # Salvar no DynamoDB
                table.put_item(Item=order_item)
                
                logger.info(f"Order {order_id} processed successfully")
                processed_orders += 1
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message: {str(e)}")
                failed_orders += 1
            except ClientError as e:
                logger.error(f"DynamoDB error: {str(e)}")
                failed_orders += 1
            except Exception as e:
                logger.error(f"Error processing order: {str(e)}")
                failed_orders += 1
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': processed_orders,
                'failed': failed_orders
            })
        }
        
    except Exception as e:
        logger.error(f"Critical error in lambda handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
```

Requisitos dos testes:
- Utilize pytest como framework de testes
- Mocke serviços AWS com moto para DynamoDB
- Teste cenários de sucesso e falha
- Verifique o tratamento correto de exceções
- Verifique a estrutura correta dos dados salvos no DynamoDB
- Teste a manipulação de erros de formato de mensagem

A função Lambda é acionada por eventos SQS e realiza o processamento de pedidos para salvá-los em uma tabela DynamoDB.
```

## Output Esperado

A IA deve gerar código completo para testes da função Lambda, incluindo:

```python
# tests/test_lambda_function.py
import json
import os
import boto3
import pytest
from moto import mock_dynamodb
from unittest import mock
import uuid
from datetime import datetime
from freezegun import freeze_time

# Importar a função Lambda
from lambda_function import lambda_handler

# Mock para uuid.uuid4 para tornar os testes determinísticos
@pytest.fixture
def mock_uuid():
    with mock.patch('uuid.uuid4', return_value='12345678-1234-5678-1234-567812345678'):
        yield

# Mock para datetime.now para tornar os testes determinísticos
@pytest.fixture
def mock_datetime():
    with freeze_time("2023-01-01T12:00:00"):
        yield

# Fixture para criar a tabela DynamoDB mockada
@pytest.fixture
def dynamodb_table():
    with mock_dynamodb():
        # Configurar variável de ambiente
        os.environ['ORDERS_TABLE'] = 'orders'
        
        # Criar o recurso do DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Criar a tabela
        table = dynamodb.create_table(
            TableName='orders',
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        yield table
        
        # Cleanup
        table.delete()
        
# Fixture para criar um evento SQS válido
@pytest.fixture
def valid_sqs_event():
    return {
        'Records': [
            {
                'messageId': '059f36b4-87a3-44ab-83d2-661975830a7d',
                'body': json.dumps({
                    'customer_id': 'cust123',
                    'items': [
                        {'product_id': 'prod1', 'quantity': 2, 'price': 10.0},
                        {'product_id': 'prod2', 'quantity': 1, 'price': 15.0}
                    ]
                })
            }
        ]
    }

# Fixture para criar um evento SQS inválido (JSON ruim)
@pytest.fixture
def invalid_json_sqs_event():
    return {
        'Records': [
            {
                'messageId': '059f36b4-87a3-44ab-83d2-661975830a7d',
                'body': '{invalid-json'
            }
        ]
    }

# Fixture para criar um evento SQS com dados incompletos
@pytest.fixture
def incomplete_data_sqs_event():
    return {
        'Records': [
            {
                'messageId': '059f36b4-87a3-44ab-83d2-661975830a7d',
                'body': json.dumps({
                    'customer_id': 'cust123'
                    # 'items' está faltando
                })
            }
        ]
    }

# Fixture para mock de contexto Lambda
@pytest.fixture
def lambda_context():
    context = mock.Mock()
    context.function_name = 'order-processor'
    context.aws_request_id = 'request-id-1'
    context.log_group_name = '/aws/lambda/order-processor'
    context.log_stream_name = '2023/01/01/[$LATEST]abcdef123456'
    context.get_remaining_time_in_millis.return_value = 10000  # 10 segundos
    return context

class TestLambdaHandler:
    
    def test_successful_processing(self, dynamodb_table, valid_sqs_event, lambda_context, mock_uuid, mock_datetime):
        """Test successful processing of a valid SQS event."""
        # Execute a função Lambda
        response = lambda_handler(valid_sqs_event, lambda_context)
        
        # Verificar resposta
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 1
        assert body['failed'] == 0
        
        # Verificar que o pedido foi salvo no DynamoDB
        saved_item = dynamodb_table.get_item(
            Key={'id': '12345678-1234-5678-1234-567812345678'}
        )
        
        # Verificar que o item existe
        assert 'Item' in saved_item
        
        # Verificar campos do item
        item = saved_item['Item']
        assert item['id'] == '12345678-1234-5678-1234-567812345678'
        assert item['customer_id'] == 'cust123'
        assert len(item['items']) == 2
        assert item['total'] == 35.0  # 2*10 + 1*15
        assert item['status'] == 'RECEIVED'
        assert item['created_at'] == '2023-01-01T12:00:00'
    
    def test_invalid_json(self, dynamodb_table, invalid_json_sqs_event, lambda_context):
        """Test processing of an event with invalid JSON."""
        # Execute a função Lambda
        response = lambda_handler(invalid_json_sqs_event, lambda_context)
        
        # Verificar resposta
        assert response['statusCode'] == 200  # A função deve continuar, mesmo com erros
        body = json.loads(response['body'])
        assert body['processed'] == 0
        assert body['failed'] == 1
        
        # Verificar que nenhum item foi adicionado ao DynamoDB
        scan_result = dynamodb_table.scan()
        assert scan_result['Count'] == 0
    
    def test_incomplete_data(self, dynamodb_table, incomplete_data_sqs_event, lambda_context):
        """Test processing of an event with incomplete data."""
        # Execute a função Lambda
        response = lambda_handler(incomplete_data_sqs_event, lambda_context)
        
        # Verificar resposta
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 0
        assert body['failed'] == 1
        
        # Verificar que nenhum item foi adicionado ao DynamoDB
        scan_result = dynamodb_table.scan()
        assert scan_result['Count'] == 0
    
    def test_multiple_records(self, dynamodb_table, lambda_context, mock_uuid, mock_datetime):
        """Test processing of multiple SQS records in a single event."""
        # Criar evento com múltiplos registros
        event = {
            'Records': [
                {
                    'messageId': '059f36b4-87a3-44ab-83d2-661975830a7d',
                    'body': json.dumps({
                        'customer_id': 'cust123',
                        'items': [
                            {'product_id': 'prod1', 'quantity': 2, 'price': 10.0}
                        ]
                    })
                },
                {
                    'messageId': '2e1424d4-f796-459a-8184-9c92662be6da',
                    'body': json.dumps({
                        'customer_id': 'cust456',
                        'items': [
                            {'product_id': 'prod3', 'quantity': 1, 'price': 25.0}
                        ]
                    })
                },
                {
                    'messageId': '3aa8b01d-93c5-43bc-a08c-3d6e1e0e0a9b',
                    'body': '{invalid-json'  # Registro inválido
                }
            ]
        }
        
        # Substituir o mock de UUID para retornar valores diferentes para cada chamada
        with mock.patch('uuid.uuid4', side_effect=['id1', 'id2']):
            # Execute a função Lambda
            response = lambda_handler(event, lambda_context)
        
        # Verificar resposta
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 2
        assert body['failed'] == 1
        
        # Verificar que os pedidos foram salvos no DynamoDB
        scan_result = dynamodb_table.scan()
        assert scan_result['Count'] == 2
    
    def test_dynamodb_error(self, lambda_context, valid_sqs_event):
        """Test handling of DynamoDB client errors."""
        # Mock para simular um erro do DynamoDB
        with mock.patch('boto3.resource') as mock_boto3:
            mock_table = mock.Mock()
            mock_table.put_item.side_effect = boto3.exceptions.ClientError(
                {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Mocked error'}},
                'PutItem'
            )
            mock_boto3.return_value.Table.return_value = mock_table
            
            # Execute a função Lambda
            response = lambda_handler(valid_sqs_event, lambda_context)
            
            # Verificar resposta
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['processed'] == 0
            assert body['failed'] == 1
    
    def test_critical_error(self, lambda_context):
        """Test handling of critical errors in the handler."""
        # Criar um evento que causará erro crítico
        # Neste caso, uma estrutura de evento completamente inválida
        event = "not-a-dict"
        
        # Execute a função Lambda
        response = lambda_handler(event, lambda_context)
        
        # Verificar resposta
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'message' in body
```

## Como Adaptar

Para usar este template:

1. Em `{DESCRICAO_FUNCIONALIDADE}`, explique o propósito da função Lambda
2. Cole o código da função Lambda em `{CODIGO_LAMBDA}`
3. Liste os serviços AWS a serem mockados em `{SERVICOS_AWS}` (ex: DynamoDB, S3, SQS)
4. Especifique `{TIPO_TRIGGER}` e `{ACAO_PRINCIPAL}` para contextualizar os testes
5. Adicione requisitos específicos de teste em `{REQUISITO_ADICIONAL}`

## Boas Práticas de Teste para Lambdas AWS

1. **Isolamento**
   - Use moto para simular serviços AWS
   - Torne os testes determinísticos com mocks para geradores aleatórios (UUID, datas)
   - Isole cada teste com fixtures apropriadas

2. **Estrutura de Eventos**
   - Simule corretamente a estrutura de eventos do trigger (SQS, API Gateway, etc.)
   - Teste variações de formatos de eventos (válidos, inválidos, limite)

3. **Cobertura**
   - Teste o caminho feliz e todos os cenários de erro
   - Verifique o tratamento correto de exceções
   - Considere testes de integração para verificar interações reais

4. **Performance**
   - Mantenha os testes rápidos para facilitar iterações
   - Use o escopo mínimo necessário para cada teste

5. **Context**
   - Forneça um mock do objeto `context` do Lambda
   - Simule timeouts e outros comportamentos do ambiente Lambda

## Configuração Recomendada para pytest

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    unit: marks tests as unit tests
    integration: marks tests as integration tests
env =
    ORDERS_TABLE=orders
    AWS_DEFAULT_REGION=us-east-1
```

## Mocks para Outros Serviços AWS

Além do DynamoDB, você pode simular outros serviços AWS com moto:

1. **S3**
```python
@pytest.fixture
def s3_bucket():
    with mock_s3():
        s3 = boto3.resource('s3', region_name='us-east-1')
        bucket = s3.create_bucket(Bucket='my-bucket')
        yield bucket
```

2. **SQS**
```python
@pytest.fixture
def sqs_queue():
    with mock_sqs():
        sqs = boto3.resource('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName='my-queue')
        yield queue
```

3. **SNS**
```python
@pytest.fixture
def sns_topic():
    with mock_sns():
        sns = boto3.resource('sns', region_name='us-east-1')
        topic = sns.create_topic(Name='my-topic')
        yield topic
```

4. **Kinesis**
```python
@pytest.fixture
def kinesis_stream():
    with mock_kinesis():
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        kinesis.create_stream(StreamName='my-stream', ShardCount=1)
        yield kinesis
``` 