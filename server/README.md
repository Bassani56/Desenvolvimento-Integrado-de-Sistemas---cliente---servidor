# Servidor Go - Reconstrução de Imagens

Servidor de alta performance em Go equivalente ao `server.py`, projetado para processar requisições de reconstrução de imagens usando algoritmos CGNE e CGNR.

## Características

- **Alta Performance**: Utiliza goroutines e channels para processamento concorrente
- **Controle de Recursos**: Monitora CPU e RAM antes de processar requisições
- **Compatibilidade Total**: Compatível com os clientes Python existentes
- **Worker Pool**: Pool de workers para processamento paralelo eficiente
- **Histórico Inteligente**: Usa histórico de execuções para estimar recursos necessários

## Requisitos

- Go 1.21 ou superior
- Bibliotecas externas (instaladas automaticamente via `go mod`)

## Instalação

```bash
cd server
go mod download
go build -o server.exe server.go  # Windows
# ou
go build -o server server.go      # Linux/Mac
```

## Execução

```bash
./server.exe  # Windows
# ou
./server      # Linux/Mac
```

O servidor iniciará na porta **7776** (localhost).

## Estrutura

- `server.go`: Código principal do servidor
- `go.mod`: Dependências do projeto
- `models/`: Diretório com modelos (model-30x30.csv, model-60x60.csv)
- `relatorio/`: Diretório onde são salvos os relatórios

## Protocolo de Comunicação

O servidor usa o mesmo protocolo do servidor Python:

**Recebe:**
```
2_|username|{"algorithm":"cgnr","model":"../server/models/model-30x30.csv","signal":"client/signals/signal-30x30-0","username":"user","idx":0}
```

**Envia:**
```json
{
  "type": "2_",
  "payload": {
    "header": {
      "username": "user",
      "index": 0,
      "algorithm": "cgnr",
      "model": "../server/models/model-30x30.csv",
      "signal": "client/signals/signal-30x30-0",
      "start_dt": "2006-01-02 15:04:05",
      "end_dt": "2006-01-02 15:04:08",
      "size": "680",
      "iters": 5,
      "time": 3.278
    },
    "image": "base64_encoded_image..."
  }
}
```

## Algoritmos Implementados

### CGNR (Conjugate Gradient Normal Residual)
- Resolve sistemas lineares usando método dos gradientes conjugados
- Versão normal residual para matrizes não quadradas

### CGNE (Conjugate Gradient Normal Error)
- Versão normal error do método dos gradientes conjugados
- Alternativa ao CGNR com propriedades diferentes de convergência

## Otimizações de Performance

1. **Worker Pool**: Pool fixo de workers (4 por padrão) para evitar criação excessiva de goroutines
2. **Channels Buffered**: Fila de requisições com buffer para melhor throughput
3. **Reutilização de Memória**: Uso eficiente de slices e buffers
4. **Processamento Assíncrono**: Cada cliente é atendido em goroutine separada
5. **Controle de Recursos**: Verifica CPU/RAM antes de processar, evitando sobrecarga

## Configuração

Constantes ajustáveis em `server.go`:

```go
const (
    MAX_WORKERS      = 4        // Número de workers simultâneos
    PORT             = "7776"    // Porta do servidor
    CPU_LIMIT        = 85.0     // Limite de CPU (%)
    MEM_LIMIT        = 85.0     // Limite de RAM (%)
    MAX_ITERATIONS   = 5        // Máximo de iterações dos algoritmos
    TOL_REQUISITO    = 1e-4     // Tolerância de convergência
)
```

## Compatibilidade

Este servidor é **100% compatível** com os clientes Python existentes. Você pode:

1. Executar o servidor Go
2. Conectar clientes Python normalmente
3. Processar requisições exatamente como antes

## Dependências

- `gonum.org/v1/gonum`: Operações de álgebra linear (matrizes e vetores)
- `github.com/shirou/gopsutil/v3`: Monitoramento de recursos do sistema (CPU/RAM)

## Notas

- O servidor usa o arquivo `teste.json` na raiz do projeto para estimar recursos necessários
- Imagens são geradas em ordem Fortran (coluna por coluna) como no servidor Python
- O formato de saída é idêntico ao servidor Python para garantir compatibilidade total

