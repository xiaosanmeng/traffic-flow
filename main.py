"""
main.py - 交通分配软件主程序
交通流优化器 (TrafficFlow Optimizer)
"""

import argparse
import sys
import time
from typing import Dict, Tuple

from network import Network
from io_handler import IOHandler
from algorithms import AssignmentAlgorithms
from visualizer import Visualizer
from evaluator import Evaluator

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='交通分配计算软件 - 交通流优化器')
    parser.add_argument('--network', '-n', type=str, default='network.json',
                       help='路网文件路径 (默认: network.json)')
    parser.add_argument('--demand', '-d', type=str, default='demand.json',
                       help='出行需求文件路径 (默认: demand.json)')
    parser.add_argument('--method', '-m', type=str, default='all',
                       choices=['all', 'aon', 'inc', 'ue'],
                       help='分配方法: all(所有方法, 默认), aon(全有全无), inc(增量分配), ue(用户均衡)')
    parser.add_argument('--output', '-o', type=str, default='results',
                       help='输出文件前缀 (默认: results)')
    
    args = parser.parse_args() # 解析命令行参数，并封装到args对象中
    
    print("="*80)
    print("交通流优化器 (TrafficFlow Optimizer)")
    print("="*80)

    
    try:
        # 1. 读取输入文件
        print("\n1. 读取输入文件...")
        network = IOHandler.read_network_json(args.network)
        od_matrix = IOHandler.read_demand_json(args.demand)
        
        # 2. 回答测试问题
        answer_test_questions(network, od_matrix)
        
        # 3. 执行交通分配
        print("\n2. 执行交通分配...")
        
        results = {}
        
        if args.method in ['all', 'aon']:
            print("\n全有全无分配 (All-or-Nothing)...")
            start_time = time.time()
            aon_flows = AssignmentAlgorithms.all_or_nothing(network, od_matrix)
            elapsed = time.time() - start_time
            print(f"完成! 用时: {elapsed:.2f}秒")
            results['All-or-Nothing'] = aon_flows
        
        if args.method in ['all', 'inc']:
            print("\n增量分配 (Incremental Assignment)...")
            start_time = time.time()
            inc_flows = AssignmentAlgorithms.incremental_assignment(network, od_matrix, increments=10)
            elapsed = time.time() - start_time
            print(f"完成! 用时: {elapsed:.2f}秒")
            results['Incremental'] = inc_flows
        
        if args.method in ['all', 'ue']:
            print("\n用户均衡分配 (User Equilibrium - Frank Wolfe)...")
            start_time = time.time()
            ue_flows = AssignmentAlgorithms.user_equilibrium_frank_wolfe(
                network, od_matrix, max_iterations=100, tolerance=1e-4
            )
            elapsed = time.time() - start_time
            print(f"完成! 用时: {elapsed:.2f}秒")
            results['User Equilibrium'] = ue_flows

        # print(results)
        
        # 4. 对每个算法保存并评估结果
        print("\n3. 评估分配结果...")
        
        # 对每个方法保存结果
        for method_name, flows in results.items():
            # 计算总出行时间
            total_time = Evaluator.calculate_total_travel_time(network, flows)
            print(f"\n{method_name} 总出行时间: {total_time:.2f} (车·分钟)")
            
            # 打印路段流量详情(方法内容和算法比较方法重复)
            # Evaluator.print_link_flow_details(network, flows)
            
            # 保存结果到文件
            output_file = f"{args.output}_{method_name.replace(' ', '_')}.csv"
            IOHandler.save_results(network, flows, output_file)
            
            # 可视化
            fig, ax = Visualizer.plot_network(
                network, 
                method_name,
                output_file,
                save_path=f"{args.output}_{method_name.replace(' ', '_')}.png"
            )
        
        print(f"\n分配完成! 结果文件已保存到 {args.output}_*.csv 和 {args.output}_*.png")

        # 比较不同算法
        if len(results) > 1:
            comparison = Evaluator.compare_algorithms(network, od_matrix, results)
            Evaluator.print_comparison_table(comparison)
        
        # 5. 显示用户均衡下的路径流量
        if 'User Equilibrium' in results:
            print("\n4. 用户均衡路径分析...")
            analyze_user_equilibrium_paths(network, od_matrix, results['User Equilibrium'])
    
    except FileNotFoundError as e:
        print(f"错误: 文件未找到 - {e}")
        # print("请使用 --create_example 参数创建示例文件")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

def answer_test_questions(network: Network, od_matrix: Dict[Tuple[str, str], float]):
    """回答测试问题"""
    print("\n测试问题解答:")
    print("-"*80)
    
    # 问题1: 不考虑拥堵的最快路径
    print("\n1. 不考虑拥堵，任意两点间的最快路径是什么？")
    print("   例如 A->F 的最短路径:")
    path_names, cost = network.get_shortest_path_by_names("A", "F")
    if path_names:
        print(f"   路径: {' -> '.join(path_names)}")
        print(f"   行程时间: {cost:.2f} 分钟 (基于自由流时间)")
    else:
        print(f"   A->F 之间没有路径")
    
    # 问题2: 考虑拥堵的最快路径（需要先分配）
    print("\n2. 假设各路段流量已知，考虑拥堵效应，任意两点之间的最快路径是什么？")
    print("   (此问题需要在分配后回答)")
    
    # 问题3: 单OD对分配
    print("\n3. 只考虑一个起讫点对的交通需求，例如 A 到 F:")
    
    # 创建单OD对需求
    single_od = {("A", "F"): 2000}
    
    print("   a) 全有全无分配:")
    aon_single = AssignmentAlgorithms.all_or_nothing(network, single_od)
    
    # 统计使用的路径
    used_links = [link_id for link_id, flow in aon_single.items() 
                  if flow > 0 and link_id < 1000]
    print(f"     使用路段数: {len(used_links)}")
    
    print("   b) 用户均衡分配:")
    ue_single = AssignmentAlgorithms.user_equilibrium_frank_wolfe(
        network, single_od, max_iterations=50, tolerance=1e-3
    )
    
    # 获取路径流量
    path_flows = AssignmentAlgorithms.get_path_flows(network, single_od, ue_single)
    
    if ("A", "F") in path_flows:
        print(f"     使用的路径数: {len(path_flows[('A', 'F')])}")
        for i, (path, flow, cost) in enumerate(path_flows[('A', 'F')], 1):
            print(f"     路径{i}: {' -> '.join(path)}, 流量: {flow:.1f}, 时间: {cost:.2f}分钟")
    
    # 问题4: 全OD对分配
    print("\n4. 考虑所有起讫点对的交通需求:")
    total_demand = sum(od_matrix.values())
    print(f"   总出行需求: {total_demand:.0f} 辆/小时")
    print(f"   OD对数量: {len(od_matrix)}")
    
    print("-"*80)

def analyze_user_equilibrium_paths(
    network: Network, 
    od_matrix: Dict[Tuple[str, str], float],
    link_flows: Dict[int, float]
):
    """分析用户均衡下的路径情况"""
    print("\n用户均衡路径详细分析:")
    print("-"*80)
    
    # 获取所有OD对的路径流量
    all_path_flows = AssignmentAlgorithms.get_path_flows(network, od_matrix, link_flows)
    
    # 分析主要OD对
    major_ods = sorted(od_matrix.items(), key=lambda x: x[1], reverse=True)
    
    for (origin, destination), demand in major_ods:
        if (origin, destination) in all_path_flows:
            paths = all_path_flows[(origin, destination)]
            print(f"\nOD对 {origin}->{destination} (需求: {demand} 辆/小时):")
            print(f"  使用路径数: {len(paths)}")
            
            # 检查路径时间是否相等（用户均衡条件）
            if len(paths) > 1:
                times = [cost for _, _, cost in paths]
                max_diff = max(times) - min(times)
                print(f"  路径时间差异: {max_diff:.4f} 分钟")
                
                if max_diff < 0.5:  # 容忍误差
                    print("  ✓ 路径时间基本相等（满足用户均衡条件）")
                else:
                    print("  ⚠ 路径时间有差异（可能未完全收敛）")
            
            total_flow = 0
            for i, (path, flow, cost) in enumerate(paths, 1):
                flow_percentage = (flow / demand) * 100
                total_flow += flow
                print(f"  路径{i}: {' -> '.join(path)}")
                print(f"      流量: {flow:.1f} 辆/小时 ({flow_percentage:.1f}%), "
                      f"时间: {cost:.2f} 分钟")
            
            # 检查流量守恒
            if abs(total_flow - demand) > 1:
                print(f"  ⚠ 流量不守恒: 总路径流量({total_flow:.1f}) ≠ OD需求({demand:.1f})")

if __name__ == "__main__":
    main()
