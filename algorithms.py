"""
algorithms.py - 交通分配算法模块
"""

import numpy as np
from typing import Dict, List, Tuple, Set
from network import Network, Link
from visualizer import Visualizer

class AssignmentAlgorithms:
    """交通分配算法集合"""
    
    @staticmethod
    def all_or_nothing(network: Network, od_matrix: Dict[Tuple[str, str], float]) -> Dict[int, float]:
        """
        全有全无分配
        所有OD流量都分配到最短路径上
        """
        # 初始化路段流量
        link_flows = {link_id: 0.0 for link_id in network.links}
        
        # 对每个OD对进行分配
        for (origin_name, destination_name), demand in od_matrix.items():
            if demand <= 0:
                continue
            
            # 获取节点ID
            origin = network.get_node_id_by_name(origin_name)
            destination = network.get_node_id_by_name(destination_name)
            
            if origin is None or destination is None:
                continue
            
            # 计算最短路径（基于自由流时间）
            path, _ = network.get_shortest_path(origin, destination)
            
            # 将流量分配到路径上
            for i in range(len(path) - 1):
                from_node = path[i]
                to_node = path[i + 1]
                link = network.get_link(from_node, to_node)
                if link:
                    link_flows[link.id] += demand
        
        return link_flows
    
    @staticmethod
    def incremental_assignment(
        network: Network, 
        od_matrix: Dict[Tuple[str, str], float], 
        increments: int = 4
    ) -> Dict[int, float]:
        """
        增量分配
        将OD需求分成若干份，逐步加载到网络中
        """
        # 初始化路段流量
        link_flows = {link_id: 0.0 for link_id in network.links}
        
        # 将每个OD需求分成increments份
        for increment in range(1, increments + 1):
            print(f"第{increment}次迭代...")
            for (origin_name, destination_name), demand in od_matrix.items():
                if demand <= 0:
                    continue
                
                # 获取节点ID
                origin = network.get_node_id_by_name(origin_name)
                destination = network.get_node_id_by_name(destination_name)
                
                if origin is None or destination is None:
                    continue
                
                # 当前增量的需求
                incremental_demand = demand / increments
                
                # 基于当前流量计算最短路径
                path, _ = network.get_shortest_path(origin, destination, link_flows)
                
                # 分配当前增量
                for i in range(len(path) - 1):
                    from_node = path[i]
                    to_node = path[i + 1]
                    link = network.get_link(from_node, to_node)
                    if link:
                        link_flows[link.id] += incremental_demand
        
        return link_flows
    
    @staticmethod
    def user_equilibrium_frank_wolfe(
        network: Network, 
        od_matrix: Dict[Tuple[str, str], float], 
        max_iterations: int = 100,
        tolerance: float = 1e-4
    ) -> Dict[int, float]:
        """
        使用Frank-Wolfe算法求解用户均衡问题
        """
        print("开始Frank-Wolfe用户均衡分配...")
        
        # 步骤1: 初始解 - 全有全无分配（自由流时间）
        print("步骤1: 初始全有全无分配")
        current_flows = AssignmentAlgorithms.all_or_nothing(network, od_matrix)
        
        iteration_log = []
        
        for iteration in range(max_iterations):
            # 步骤2: 计算当前路段行程时间
            current_times = {}
            for link_id, flow in current_flows.items():
                link = network.links[link_id]
                current_times[link_id] = link.get_travel_time(flow)
            
            # 步骤3: 计算辅助流量 - 在阻抗下做全有全无分配
            auxiliary_flows = {link_id: 0.0 for link_id in network.links}
            
            for (origin_name, destination_name), demand in od_matrix.items():
                if demand <= 0:
                    continue
                
                # 获取节点ID
                origin = network.get_node_id_by_name(origin_name)
                destination = network.get_node_id_by_name(destination_name)
                
                if origin is None or destination is None:
                    continue
                
                # 计算最短路径（基于当前阻抗）
                path, _ = network.get_shortest_path(origin, destination, current_flows)
                
                # 分配流量
                for i in range(len(path) - 1):
                    from_node = path[i]
                    to_node = path[i + 1]
                    link = network.get_link(from_node, to_node)
                    if link:
                        auxiliary_flows[link.id] += demand
            
            # 步骤4: 计算下降方向
            direction = {}
            for link_id in current_flows:
                direction[link_id] = auxiliary_flows[link_id] - current_flows[link_id]
            
            # 步骤5: 计算最优步长（二分法）
            low, high = 0.0, 1.0
            
            def objective(alpha):
                """目标函数：总出行时间"""
                total_time = 0.0
                for link_id in current_flows:
                    link = network.links[link_id]
                    flow = current_flows[link_id] + alpha * direction[link_id]
                    total_time += flow * link.get_travel_time(flow)
                return total_time
            
            # 黄金分割法求最优步长
            phi = 0.618  # 黄金比例
            a, b = low, high
            x1 = b - phi * (b - a)
            x2 = a + phi * (b - a)
            
            for _ in range(20):
                if objective(x1) < objective(x2):
                    b = x2
                    x2 = x1
                    x1 = b - phi * (b - a)
                else:
                    a = x1
                    x1 = x2
                    x2 = a + phi * (b - a)
            
            optimal_alpha = (a + b) / 2
            
            # 也可以使用简单步长公式：2/(k+2)
            # optimal_alpha = 2.0 / (iteration + 2)
            
            # 步骤6: 更新流量
            previous_flows = current_flows.copy()
            for link_id in current_flows:
                current_flows[link_id] += optimal_alpha * direction[link_id]
                # 确保流量非负
                current_flows[link_id] = max(0.0, current_flows[link_id])
            
            # 步骤7: 计算收敛指标
            gap = 0.0
            total_demand = sum(od_matrix.values())
            
            for link_id in current_flows:
                link = network.links[link_id]
                current_time = link.get_travel_time(current_flows[link_id])
                auxiliary_time = link.get_travel_time(auxiliary_flows[link_id])
                gap += (auxiliary_time - current_time) * direction[link_id]
            
            relative_gap = abs(gap) / (total_demand + 1e-10)
            
            # 计算总出行时间
            total_travel_time = 0.0
            for link_id, flow in current_flows.items():
                link = network.links[link_id]
                total_travel_time += flow * link.get_travel_time(flow)
            
            iteration_log.append({
                'iteration': iteration + 1,
                'relative_gap': relative_gap,
                'total_time': total_travel_time,
                'step_size': optimal_alpha
            })
            
            print(f"迭代 {iteration + 1}: 相对间隙 = {relative_gap:.6f}, 总时间 = {total_travel_time:.2f}, 步长 = {optimal_alpha:.4f}")
            
            # 检查收敛
            if relative_gap < tolerance:
                print(f"在第 {iteration + 1} 次迭代收敛")
                break
        
        # 记录迭代过程
        # if iteration_log:
        #     print("\n迭代过程总结:")
        #     for log in iteration_log[-5:]:  # 显示最后5次迭代
        #         print(f"迭代 {log['iteration']}: 相对间隙 = {log['relative_gap']:.6f}")
        # Visualizer.plot_convergence(iteration_log, 'convergence.png')
        
        return current_flows
    
    @staticmethod
    def get_path_flows(
        network: Network, 
        od_matrix: Dict[Tuple[str, str], float], 
        link_flows: Dict[int, float]
    ) -> Dict[Tuple[str, str], List[Tuple[List[str], float, float]]]:
        """
        获取每个OD对使用的路径及其流量
        使用流量加载方法估计路径流量
        """
        path_flows = {}
        
        for (origin_name, destination_name), demand in od_matrix.items():
            if demand <= 0:
                continue
            
            # 获取节点ID
            origin = network.get_node_id_by_name(origin_name)
            destination = network.get_node_id_by_name(destination_name)
            
            if origin is None or destination is None:
                continue
            
            # 获取多条可能路径
            paths = network.get_all_shortest_paths(origin, destination)
            
            # 简单估计：根据路径成本分配流量
            if not paths:
                continue
            
            # 计算每条路径的阻抗（基于最终流量）
            path_costs = []
            path_names_list = []
            
            for path, _ in paths:
                # 将节点ID转换为名称
                path_names = [network.get_node_name_by_id(node_id) for node_id in path]
                path_names_list.append(path_names)
                
                cost = 0.0
                for i in range(len(path) - 1):
                    from_node = path[i]
                    to_node = path[i + 1]
                    link = network.get_link(from_node, to_node)
                    if link:
                        cost += link.get_travel_time(link_flows.get(link.id, 0))
                path_costs.append(cost)
            
            # 使用Logit模型分配流量（简化）
            if path_costs:
                min_cost = min(path_costs)
                total_weight = 0.0
                weights = []
                
                for cost in path_costs:
                    # 阻抗差较大时，权重较小
                    weight = np.exp(-0.5 * (cost - min_cost))  # θ=0.5
                    weights.append(weight)
                    total_weight += weight
                
                # 分配流量
                path_info = []
                for path_names, weight, cost in zip(path_names_list, weights, path_costs):
                    if total_weight > 0:
                        flow = demand * weight / total_weight
                    else:
                        flow = demand / len(paths)
                    path_info.append((path_names, flow, cost))
                
                path_flows[(origin_name, destination_name)] = path_info
        
        return path_flows