#!/usr/bin/env python3
"""
Script para comparar relatórios de performance entre servidor Python e Go.

Uso:
    python comparar_performance.py <arquivo_python.csv> <arquivo_go.csv>

Exemplo:
    python comparar_performance.py server/relatorio/performance-relatorio_1234567890.csv server/relatorio/performance-relatorio_1234567891.csv
"""

import sys
import csv
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from pathlib import Path
import argparse


def parse_percentage(value_str):
    """Extrai valor numérico de string como '    45.2%'"""
    try:
        # Remove espaços e %
        cleaned = value_str.strip().replace('%', '').strip()
        return float(cleaned)
    except:
        return 0.0


def load_performance_csv(filepath):
    """Carrega CSV de performance e retorna dados estruturados"""
    timestamps = []
    cpu_values = []
    mem_values = []
    server_name = "Unknown"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Pula cabeçalho
            
            # Verifica se tem coluna Server
            has_server_col = len(header) > 3 and "Server" in header[-1]
            
            for row in reader:
                if len(row) < 3:
                    continue
                
                timestamp_str = row[0].strip()
                cpu_str = row[1].strip()
                mem_str = row[2].strip()
                
                # Extrai nome do servidor se disponível
                if has_server_col and len(row) > 3:
                    server_name = row[3].strip()
                
                try:
                    # Converte timestamp para datetime
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    cpu = parse_percentage(cpu_str)
                    mem = parse_percentage(mem_str)
                    
                    timestamps.append(timestamp)
                    cpu_values.append(cpu)
                    mem_values.append(mem)
                except Exception as e:
                    print(f"Aviso: Erro ao processar linha: {e}")
                    continue
        
        return {
            'timestamps': np.array(timestamps),
            'cpu': np.array(cpu_values),
            'mem': np.array(mem_values),
            'server': server_name,
            'filename': Path(filepath).name
        }
    except Exception as e:
        print(f"Erro ao carregar {filepath}: {e}")
        return None


def calculate_statistics(data):
    """Calcula estatísticas básicas"""
    return {
        'cpu_mean': np.mean(data['cpu']),
        'cpu_std': np.std(data['cpu']),
        'cpu_min': np.min(data['cpu']),
        'cpu_max': np.max(data['cpu']),
        'mem_mean': np.mean(data['mem']),
        'mem_std': np.std(data['mem']),
        'mem_min': np.min(data['mem']),
        'mem_max': np.max(data['mem']),
        'count': len(data['cpu'])
    }


def normalize_timestamps(data1, data2):
    """Normaliza timestamps para começar do zero (em segundos)"""
    # Encontra o timestamp inicial mais antigo
    start_time = min(data1['timestamps'][0], data2['timestamps'][0])
    
    # Converte para segundos desde o início
    time1 = [(t - start_time).total_seconds() for t in data1['timestamps']]
    time2 = [(t - start_time).total_seconds() for t in data2['timestamps']]
    
    return time1, time2


def plot_comparison(data1, data2, output_file='comparacao_performance.png'):
    """Gera gráficos comparativos"""
    # Normaliza timestamps
    time1, time2 = normalize_timestamps(data1, data2)
    
    # Cria figura com subplots
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Comparação de Performance: Servidor Python vs Go', fontsize=16, fontweight='bold')
    
    # Gráfico 1: CPU Usage
    ax1 = axes[0]
    ax1.plot(time1, data1['cpu'], label=f"{data1['server']} (CPU)", 
             color='#2E86AB', linewidth=2, alpha=0.8)
    ax1.plot(time2, data2['cpu'], label=f"{data2['server']} (CPU)", 
             color='#A23B72', linewidth=2, alpha=0.8)
    ax1.set_xlabel('Tempo (segundos)', fontsize=12)
    ax1.set_ylabel('Uso de CPU (%)', fontsize=12)
    ax1.set_title('Uso de CPU ao Longo do Tempo', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)
    
    # Gráfico 2: Memory Usage
    ax2 = axes[1]
    ax2.plot(time1, data1['mem'], label=f"{data1['server']} (RAM)", 
             color='#2E86AB', linewidth=2, alpha=0.8)
    ax2.plot(time2, data2['mem'], label=f"{data2['server']} (RAM)", 
             color='#A23B72', linewidth=2, alpha=0.8)
    ax2.set_xlabel('Tempo (segundos)', fontsize=12)
    ax2.set_ylabel('Uso de Memória (%)', fontsize=12)
    ax2.set_title('Uso de Memória ao Longo do Tempo', fontsize=14, fontweight='bold')
    ax2.legend(loc='best', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(bottom=0)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Gráfico salvo em: {output_file}")
    
    # Gráfico adicional: Box plots comparativos
    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 6))
    fig2.suptitle('Distribuição de Uso de Recursos', fontsize=16, fontweight='bold')
    
    # Box plot CPU
    ax3 = axes2[0]
    box_data_cpu = [data1['cpu'], data2['cpu']]
    bp1 = ax3.boxplot(box_data_cpu, labels=[data1['server'], data2['server']], 
                      patch_artist=True)
    bp1['boxes'][0].set_facecolor('#2E86AB')
    bp1['boxes'][1].set_facecolor('#A23B72')
    ax3.set_ylabel('Uso de CPU (%)', fontsize=12)
    ax3.set_title('Distribuição de CPU', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Box plot Memory
    ax4 = axes2[1]
    box_data_mem = [data1['mem'], data2['mem']]
    bp2 = ax4.boxplot(box_data_mem, labels=[data1['server'], data2['server']], 
                      patch_artist=True)
    bp2['boxes'][0].set_facecolor('#2E86AB')
    bp2['boxes'][1].set_facecolor('#A23B72')
    ax4.set_ylabel('Uso de Memória (%)', fontsize=12)
    ax4.set_title('Distribuição de Memória', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    boxplot_file = output_file.replace('.png', '_boxplot.png')
    plt.savefig(boxplot_file, dpi=300, bbox_inches='tight')
    print(f"✓ Box plots salvos em: {boxplot_file}")


def print_statistics(stats1, stats2, name1, name2):
    """Imprime estatísticas comparativas"""
    print("\n" + "="*80)
    print("ESTATÍSTICAS COMPARATIVAS".center(80))
    print("="*80)
    
    print(f"\n📊 {name1}:")
    print(f"   CPU - Média: {stats1['cpu_mean']:.2f}% | "
          f"Desvio: {stats1['cpu_std']:.2f}% | "
          f"Min: {stats1['cpu_min']:.2f}% | "
          f"Max: {stats1['cpu_max']:.2f}%")
    print(f"   RAM - Média: {stats1['mem_mean']:.2f}% | "
          f"Desvio: {stats1['mem_std']:.2f}% | "
          f"Min: {stats1['mem_min']:.2f}% | "
          f"Max: {stats1['mem_max']:.2f}%")
    print(f"   Total de medições: {stats1['count']}")
    
    print(f"\n📊 {name2}:")
    print(f"   CPU - Média: {stats2['cpu_mean']:.2f}% | "
          f"Desvio: {stats2['cpu_std']:.2f}% | "
          f"Min: {stats2['cpu_min']:.2f}% | "
          f"Max: {stats2['cpu_max']:.2f}%")
    print(f"   RAM - Média: {stats2['mem_mean']:.2f}% | "
          f"Desvio: {stats2['mem_std']:.2f}% | "
          f"Min: {stats2['mem_min']:.2f}% | "
          f"Max: {stats2['mem_max']:.2f}%")
    print(f"   Total de medições: {stats2['count']}")
    
    print(f"\n📈 DIFERENÇAS:")
    cpu_diff = stats2['cpu_mean'] - stats1['cpu_mean']
    mem_diff = stats2['mem_mean'] - stats1['mem_mean']
    
    print(f"   CPU: {name2} usa {abs(cpu_diff):.2f}% {'mais' if cpu_diff > 0 else 'menos'} que {name1}")
    print(f"   RAM: {name2} usa {abs(mem_diff):.2f}% {'mais' if mem_diff > 0 else 'menos'} que {name1}")
    
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Compara relatórios de performance entre servidor Python e Go',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python comparar_performance.py server/relatorio/performance-relatorio_123.csv server/relatorio/performance-relatorio_456.csv
  
  python comparar_performance.py arquivo1.csv arquivo2.csv -o resultado.png
        """
    )
    
    parser.add_argument('arquivo1', help='Primeiro arquivo CSV (geralmente Python)')
    parser.add_argument('arquivo2', help='Segundo arquivo CSV (geralmente Go)')
    parser.add_argument('-o', '--output', default='comparacao_performance.png',
                       help='Nome do arquivo de saída do gráfico (padrão: comparacao_performance.png)')
    
    args = parser.parse_args()
    
    # Carrega dados
    print(f"📂 Carregando {args.arquivo1}...")
    data1 = load_performance_csv(args.arquivo1)
    if data1 is None:
        print("❌ Erro ao carregar primeiro arquivo")
        sys.exit(1)
    
    print(f"📂 Carregando {args.arquivo2}...")
    data2 = load_performance_csv(args.arquivo2)
    if data2 is None:
        print("❌ Erro ao carregar segundo arquivo")
        sys.exit(1)
    
    print(f"✓ Dados carregados: {data1['server']} ({len(data1['cpu'])} medições) vs {data2['server']} ({len(data2['cpu'])} medições)")
    
    # Calcula estatísticas
    stats1 = calculate_statistics(data1)
    stats2 = calculate_statistics(data2)
    
    # Imprime estatísticas
    print_statistics(stats1, stats2, data1['server'], data2['server'])
    
    # Gera gráficos
    print("📊 Gerando gráficos...")
    plot_comparison(data1, data2, args.output)
    
    print("\n✅ Análise concluída!")


if __name__ == '__main__':
    main()

