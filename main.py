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
                       help='输出文件路径 (默认: results)')
    
    args = parser.parse_args() # 解析命令行参数，并封装到args对象中
    
    print("="*80)
    print("交通流优化器 (TrafficFlow Optimizer)")
    print("="*80)

    
    try:
        # 1. 读取输入文件
        print("\n1. 读取输入文件...")
        network = IOHandler.read_network_json(args.network)
        od_matrix = IOHandler.read_demand_json(args.demand)
        
        # 2. 执行交通分配
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
            ue_flows, iteration_log = AssignmentAlgorithms.user_equilibrium_frank_wolfe(
                network, od_matrix, max_iterations=100, tolerance=1e-4
            )
            elapsed = time.time() - start_time
            print(f"完成! 用时: {elapsed:.2f}秒")
            results['User-Equilibrium'] = ue_flows

        # print(results)
        
        # 3. 对每个算法结果保存、可视化并评估
        print("\n3. 评估分配结果...")
        
        # 对每个方法保存结果
        for method_name, flows in results.items():
            # 计算总出行时间
            total_time = Evaluator.calculate_total_travel_time(network, flows)
            print(f"\n{method_name} 总出行时间: {total_time:.2f} (车·小时)")
            
            # 打印路段流量详情(方法内容和算法比较方法重复)
            Evaluator.print_link_flow_details(network, flows)
            
            # 保存结果到文件
            output_file = f"./{args.output}/{method_name.replace(' ', '_')}.csv"
            IOHandler.save_results(network, flows, output_file)
            
            # 可视化
            fig, ax = Visualizer.plot_network(
                network, 
                method_name,
                output_file,
                save_path=f"./{args.output}/{method_name.replace(' ', '_')}.png"
            )
            
            # 可视化收敛曲线
            Visualizer.plot_convergence(
                iteration_log,
                save_path=f"./{args.output}/convergence.png"
            )
        
        print(f"\n分配完成! 结果文件已保存到 {args.output}/*.csv 和 {args.output}/*.png")

        # 比较不同算法
        if len(results) > 1:
            comparison = Evaluator.compare_algorithms(network, od_matrix, results, csv_file_path=f"./{args.output}")
            Evaluator.print_comparison_table(comparison)
        
        # # 5. 显示用户均衡下的路径流量
        # if 'User Equilibrium' in results:
        #     print("\n4. 用户均衡路径分析...")
        #     analyze_user_equilibrium_paths(network, od_matrix, results['User Equilibrium'])

        # 5. 回答测试问题
        answer_test_questions(network, od_matrix)
    
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
    
    while True:
        print("\n请选择要回答的问题:")
        print("1. 不考虑拥堵，任意两点间的最快路径是什么？")
        print("2. 考虑拥堵效应，任意两点之间的最快路径是什么？")
        print("3. 单OD对交通分配分析（例如A到F）")
        print("4. 全OD对交通分配统计")
        print("5. 退出系统")
        
        try:
            choice = input("\n请输入选项编号(1-5): ").strip()
            
            if choice == "5":
                print("感谢使用，再见！")
                break
                
            if choice not in ["1", "2", "3", "4"]:
                print("无效选项，请重新输入！")
                continue
            
            # 问题1：不考虑拥堵的最快路径
            if choice == "1":
                origin = input("请输入起点名称（如A）: ").strip().upper()
                destination = input("请输入终点名称（如F）: ").strip().upper()
                
                if origin not in [node.name for node in network.nodes.values()]:
                    print(f"错误：起点'{origin}'不存在！")
                    continue
                if destination not in [node.name for node in network.nodes.values()]:
                    print(f"错误：终点'{destination}'不存在！")
                    continue
                
                print(f"\n计算{origin}到{destination}的最快路径（基于自由流时间）:")
                path, _ = network.get_shortest_path(network.get_node_id_by_name(origin), network.get_node_id_by_name(destination))
                print(f"最快路径: {' -> '.join(network.get_node_name_by_id(item) for item in path)}")

            # 问题2：考虑拥堵的最快路径
            elif choice == "2":
                origin = input("请输入起点名称（如A）: ").strip().upper()
                destination = input("请输入终点名称（如F）: ").strip().upper()
                
                if origin not in [node.name for node in network.nodes.values()]:
                    print(f"错误：起点'{origin}'不存在！")
                    continue
                if destination not in [node.name for node in network.nodes.values()]:
                    print(f"错误：终点'{destination}'不存在！")
                    continue

                print('请输入各路段流量（格式：link_id:flow, 如1:100,1000:200,2:300,2000:400, 其中1000/2000表示路段1/2的反向路段）:')
                link_flows_input = input().strip()
                link_flows = {link_id: 0.0 for link_id in network.links}
                if not link_flows_input:
                    print("未输入任何路段流量，初始化为0")
                else:
                    for item in link_flows_input.split(','):
                        link_id, flow = item.split(':')
                        link_flows[int(link_id)] = float(flow)
                
                print(f"\n计算{origin}到{destination}的最快路径（基于给定流量）:")
                path, _ = network.get_shortest_path(network.get_node_id_by_name(origin), network.get_node_id_by_name(destination), 
                                                   link_flows)
                print(f"最快路径: {' -> '.join(network.get_node_name_by_id(item) for item in path)}")   
                
            # 问题3：单OD对交通分配分析
            elif choice == "3":
                origin = input("请输入起点名称（如A）: ").strip().upper()
                destination = input("请输入终点名称（如F）: ").strip().upper()
                
                if origin not in [node.name for node in network.nodes.values()]:
                    print(f"错误：起点'{origin}'不存在！")
                    continue
                if destination not in [node.name for node in network.nodes.values()]:
                    print(f"错误：终点'{destination}'不存在！")
                    continue

                od_demand = float(input(f"请输入{origin}到{destination}的交通需求量（辆/小时）: "))
                single_od = {(origin, destination): od_demand}
                print("\n全有全无分配结果:")
                aon_flows = AssignmentAlgorithms.all_or_nothing(network, single_od)
                
                # 统计使用的路段
                used_links_aon = []
                for link_id, flow in aon_flows.items():
                    if flow > 0 and link_id < 1000:  # 只统计原始路段
                        link = network.links[link_id]
                        used_links_aon.append((link, flow))
                
                print(f"   使用的路段数: {len(used_links_aon)}")
                print(f"   使用的路段详情:")
                for link, flow in used_links_aon:
                    vc_ratio = flow / link.capacity if link.capacity > 0 else 0
                    print(f"     {link.from_name}→{link.to_name}: "
                          f"流量={flow:.0f}, 容量={link.capacity}, V/C={vc_ratio:.2f}")
                
                # 获取路径信息
                aon_path_names, aon_cost = network.get_shortest_path_by_names(origin, destination)
                print(f"   唯一路径: {' → '.join(aon_path_names)}")
                print(f"   路径时间: {aon_cost:.2f} 分钟")


            elif choice == "4":
                print("已用三种算法对交通流进行分配，并给出各路段流量及出行总时间")


        except KeyboardInterrupt:
            print("\n\n程序被中断")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            import traceback
            traceback.print_exc()
            input("按Enter键继续...")

                
            


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
