# Melhores Práticas para Prompts AWS Python

Este guia fornece boas práticas para criar prompts eficazes para gerar código Python para AWS Lambda e ECS usando IA.

## Princípios Gerais

### 1. Seja específico e detalhado

- **Ruim**: "Crie uma função Lambda"
- **Bom**: "Crie uma função Lambda Python 3.9 que consome eventos do SQS, valida mensagens usando Pydantic e salva os dados no DynamoDB"

### 2. Forneça contexto

Inclua informações sobre:
- Versão do Python
- Serviços AWS que serão utilizados
- Bibliotecas/frameworks preferidos
- Padrões de arquitetura

### 3. Divida tarefas complexas

Para aplicações maiores, solicite código em etapas:
1. Primeiro a estrutura do projeto
2. Depois modelos/entidades
3. Em seguida lógica de negócios
4. Por fim testes e configuração de infraestrutura

## Prompts para Lambda

### Estrutura básica de um prompt para Lambda

```
Crie uma função AWS Lambda em Python 3.9 que:

1. Objetivo: [processamento de pedidos, autenticação de usuários, etc]
2. Entrada: [eventos do SQS, API Gateway, CloudWatch, etc]
3. Processamento: [validação, transformação, cálculos, etc]
4. Saída: [salvar no DynamoDB, retornar resposta API, publicar no SNS, etc]
5. Dependências: [boto3, requests, pydantic, etc]
6. Configuração: [timeout, memória, variáveis de ambiente]

A estrutura do código deve seguir o padrão [simples/repository/clean architecture] e incluir testes unitários.
```

## Lidando com Limitações

### 1. Tamanho do código

Para projetos maiores, solicite:
- Primeiro a estrutura de diretórios
- Lista de arquivos necessários
- Cada arquivo individualmente

### 2. Conhecimento desatualizado

Especifique versões de SDKs e bibliotecas para evitar código incompatível.

### 3. Contexto limitado

Referencie partes do código já gerado ao solicitar adições ou modificações.

## Iteração de Código com IA

### 1. Revise criticamente antes de implementar

Sempre verifique:
- Tratamento de erros
- Configurações sensíveis como timeouts e retries
- Segurança (não acumular secrets em código)
- Uso de recursos AWS (permissões mínimas)

### 2. Estratégias para refinar código gerado

1. **Técnica de refinamento incremental**:
   ```
   O código gerado tem um problema: [descrição específica].
   
   [código problemático]
   
   Por favor, refine o código considerando [requisito específico].
   ```

2. **Técnica de expansão de funcionalidade**:
   ```
   Este código funciona bem:
   [código existente]
   
   Agora, adicione [nova funcionalidade] mantendo a mesma estrutura e estilo.
   ```

3. **Técnica de comparação de alternativas**:
   ```
   Você gerou esta solução:
   [solução A]
   
   Poderia gerar uma implementação alternativa usando [abordagem diferente]?
   Depois explique as vantagens e desvantagens de cada abordagem.
   ```

### 3. Lidar com erros comuns de IA

| Erro comum | Como corrigir |
|------------|--------------|
| Importações faltando | "Adicione todas as importações necessárias no topo do arquivo" |
| Não segue padrões | "Refatore o código para seguir o padrão Repository mostrado em [exemplo]" |
| Código incompatível | "Atualize o código para usar async/await corretamente em todas as funções" |
| Testes incompletos | "Adicione testes para cenários de erro e edge cases" |

## Exemplos de Prompts Eficazes

### Lambda Básica com DynamoDB

```
Crie uma função AWS Lambda em Python 3.9 que armazena registros de eventos no DynamoDB.
- Use boto3 para interagir com o DynamoDB
- Implemente um padrão repository simples
- Inclua tratamento de erros e retries com backoff exponencial
- Adicione logs estruturados usando o módulo logging
- Inclua testes unitários usando pytest e moto
```

### Microserviço no ECS

```
Crie um microserviço Python para AWS ECS que:
- Usa FastAPI como framework web
- Se conecta a um banco de dados PostgreSQL via SQLAlchemy
- Implementa autenticação JWT
- Segue princípios de Clean Architecture
- Inclui Dockerfile e configuração de docker-compose para desenvolvimento local
```

## Resolução de Problemas Comuns

### 1. Código gerado não executa

Solicite à IA:
```
O código gerou este erro:
[mensagem de erro]

Aqui está o código problemático:
[trecho de código]

Por favor, corrija o código e explique o que causou o erro.
```

### 2. Código não segue a arquitetura especificada

Peça reconciliação:
```
O código gerado não segue Clean Architecture porque [razão específica].

Refatore-o para que:
1. A entidade fique na camada de domínio
2. O UseCase não conheça detalhes de infraestrutura
3. A implementação do repositório esteja na camada de infraestrutura
```

### 3. AWS SDK usado incorretamente

Solicite correção específica:
```
A chamada ao DynamoDB está incorreta:
[código incorreto]

A forma correta de implementar batch_writer com erro-handling é:
[exemplo ou descrição]

Por favor, corrija esta implementação específica.
``` 