# Comparação de Performance - Servidor Python vs Go

Script para comparar e visualizar métricas de performance entre os servidores Python e Go.

## Requisitos

```bash
pip install matplotlib numpy
```

## Uso Básico

```bash
python comparar_performance.py <arquivo_python.csv> <arquivo_go.csv>
```

## Exemplo

```bash
python comparar_performance.py server/relatorio/performance-relatorio_1764885256.csv server/relatorio/performance-relatorio_1764819600.csv
```

## Opções

```bash
python comparar_performance.py arquivo1.csv arquivo2.csv -o resultado.png
```

- `-o, --output`: Nome do arquivo de saída (padrão: `comparacao_performance.png`)

## O que o script faz

1. **Carrega os CSVs** de ambos os servidores
2. **Calcula estatísticas**:
   - Média, desvio padrão, mínimo e máximo de CPU e RAM
   - Total de medições
3. **Gera gráficos**:
   - **Gráfico temporal**: CPU e RAM ao longo do tempo (sobrepostos)
   - **Box plots**: Distribuição comparativa de CPU e RAM
4. **Imprime relatório** com todas as estatísticas comparativas

## Formato dos CSVs

Os CSVs devem ter o formato:
```
Measured at   ,CPU usage   ,Memory usage,Server
2025-12-04 18:54:17,"    18.4%","    41.0%",Python
2025-12-04 18:54:18,"    28.1%","    41.0%",Python
...
```

## Arquivos Gerados

- `comparacao_performance.png`: Gráficos temporais de CPU e RAM
- `comparacao_performance_boxplot.png`: Box plots comparativos

## Notas

- O script detecta automaticamente qual servidor gerou cada CSV (coluna "Server")
- Se a coluna "Server" não existir, usa o nome do arquivo
- Os timestamps são normalizados para começar do zero para melhor comparação visual

