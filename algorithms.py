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
        """全有全无分配"""
        link_flows = {link_id: 0.0 for link_id in network.links}
        
        for (origin_name, destination_name), demand in od_matrix.items():
            if demand <= 0:
                continue
            
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
        increments: int = 10
    ) -> Dict[int, float]:
        """增量分配"""
        link_flows = {link_id: 0.0 for link_id in network.links}
        
        for increment in range(1, increments + 1):
            print(f"第{increment}次迭代...")
            for (origin_name, destination_name), demand in od_matrix.items():
                if demand <= 0:
                    continue
                
                origin = network.get_node_id_by_name(origin_name)
                destination = network.get_node_id_by_name(destination_name)
                
                if origin is None or destination is None:
                    continue
                
                incremental_demand = demand / increments
                
                # 基于当前流量计算最短路径
                path, _ = network.get_shortest_path(origin, destination, link_flows)
                
                for i in range(len(path) - 1):
                    from_node = path[i]
                    to_node = path[i + 1]
                    link = network.get_link(from_node, to_node)
                    if link:
                        link_flows[link.id] += incremental_demand
        
        return link_flows
    
    @staticmethod
    def _objective_function(network: Network, base_flows: Dict[int, float], 
                          direction: Dict[int, float], alpha: float) -> float:
        """
        计算目标函数值（总出行时间）单位：车·小时
        """
        total_time = 0.0
        for link_id, base_flow in base_flows.items():
            link = network.links[link_id]
            flow = base_flow + alpha * direction[link_id]
            flow = max(0.0, flow)  # 确保非负
            
            # link.get_travel_time() 返回分钟，转换为小时
            travel_time_hours = link.get_travel_time(flow) / 60.0
            total_time += flow * travel_time_hours  # 车·小时
        
        return total_time
    
    @staticmethod
    def _golden_section_search(network: Network, base_flows: Dict[int, float], 
                              direction: Dict[int, float], max_iter: int = 30) -> float:
        """
        黄金分割法搜索最优步长
        """
        phi = 0.618033988749895  # 黄金比例
        a, b = 0.0, 1.0
        
        # 检查边界值
        f_a = AssignmentAlgorithms._objective_function(network, base_flows, direction, a)
        f_b = AssignmentAlgorithms._objective_function(network, base_flows, direction, b)
        
        # 如果方向为零，直接返回
        # if np.allclose(list(direction.values()), 0, atol=1e-6):
        #     return 0.0
        max_dir = max(abs(d) for d in direction.values())
        if max_dir < 1e-8:
            return 0.0
        
        # 初始化两个黄金分割点
        x1 = b - phi * (b - a)
        x2 = a + phi * (b - a)
        f1 = AssignmentAlgorithms._objective_function(network, base_flows, direction, x1)
        f2 = AssignmentAlgorithms._objective_function(network, base_flows, direction, x2)
        
        # 黄金分割法主循环
        # for i in range(max_iter):
        #     if f1 < f2:
        #         b = x2
        #         x2 = x1
        #         f2 = f1
        #         x1 = b - phi * (b - a)
        #         f1 = AssignmentAlgorithms._objective_function(network, base_flows, direction, x1)
        #     else:
        #         a = x1
        #         x1 = x2
        #         f1 = f2
        #         x2 = a + phi * (b - a)
        #         f2 = AssignmentAlgorithms._objective_function(network, base_flows, direction, x2)
            
        #     # 如果区间足够小，提前结束
        #     if (b - a) < 1e-6:
        #         break

        # 黄金分割法主循环
        for i in range(max_iter):
            if f1 < f2:
                # 最小值在 [a, x2] 区间
                b = x2
                f_b = f2
                x2 = x1
                f2 = f1
                x1 = b - phi * (b - a)
                f1 = AssignmentAlgorithms._objective_function(network, base_flows, direction, x1)
            else:
                # 最小值在 [x1, b] 区间
                a = x1
                f_a = f1
                x1 = x2
                f1 = f2
                x2 = a + phi * (b - a)
                f2 = AssignmentAlgorithms._objective_function(network, base_flows, direction, x2)
            
            # 收敛检查：区间足够小或函数值变化很小
            if (b - a) < 1e-4:
                break
            
            # 检查函数值是否不再显著变化
            if i > 5 and abs(f1 - f2) < 1e-6 * max(abs(f1), abs(f2), 1.0):
                break
        
        optimal_alpha = (a + b) / 2
        optimal_alpha = max(0.0, min(1.0, optimal_alpha))
        
        # # 检查步长是否过小
        # if optimal_alpha < 1e-4 and i > 0:
        #     # 使用MSA步长作为备选
        #     return 1.0 / (i + 2)
        
        return optimal_alpha
    
    @staticmethod
    def user_equilibrium_frank_wolfe(
        network: Network, 
        od_matrix: Dict[Tuple[str, str], float], 
        max_iterations: int = 200,
        tolerance: float = 1e-3
    ) -> Tuple[Dict[int, float], List[Dict]]:
        """
        使用Frank-Wolfe算法求解用户均衡问题
        返回: (流量字典, 迭代日志)
        """
        print("开始Frank-Wolfe用户均衡分配...")
        
        # 步骤1: 初始解
        print("步骤1: 初始全有全无分配")
        current_flows = AssignmentAlgorithms.all_or_nothing(network, od_matrix)
        
        iteration_log = []
        total_demand = sum(od_matrix.values())
        
        for iteration in range(max_iterations):
            
            current_times_minutes = {}
            for link_id, flow in current_flows.items():
                link = network.links[link_id]
                current_times_minutes[link_id] = link.get_travel_time(flow)
            
            # 步骤2: 计算辅助流量
            auxiliary_flows = {link_id: 0.0 for link_id in network.links}
            
            for (origin_name, destination_name), demand in od_matrix.items():
                if demand <= 0:
                    continue
                
                origin = network.get_node_id_by_name(origin_name)
                destination = network.get_node_id_by_name(destination_name)
                
                if origin is None or destination is None:
                    continue
                
                # 基于当前阻抗计算最短路径
                path, _ = network.get_shortest_path(origin, destination, current_flows)
                
                for i in range(len(path) - 1):
                    from_node = path[i]
                    to_node = path[i + 1]
                    link = network.get_link(from_node, to_node)
                    if link:
                        auxiliary_flows[link.id] += demand
            
            # 步骤3: 计算下降方向
            direction = {}
            for link_id in current_flows:
                direction[link_id] = auxiliary_flows[link_id] - current_flows[link_id]
            
            # 步骤4: 计算最优步长
            optimal_alpha = AssignmentAlgorithms._golden_section_search(
                network, current_flows, direction
            )
            
            # 如果黄金分割法失败，使用MSA步长
            if optimal_alpha < 1e-4:
                optimal_alpha = 1.0 / (iteration + 2)
            
            # 步骤5: 更新流量
            previous_flows = current_flows.copy()
            for link_id in current_flows:
                current_flows[link_id] += optimal_alpha * direction[link_id]
                current_flows[link_id] = max(0.0, current_flows[link_id])
            
            # 步骤6: 计算收敛指标
            gap = 0.0
            for link_id in current_flows:
                link = network.links[link_id]
                # 当前流量下的行程时间（分钟）
                current_time_min = link.get_travel_time(current_flows[link_id])
                # 辅助流量下的行程时间（分钟）
                auxiliary_time_min = link.get_travel_time(auxiliary_flows[link_id])
                # 转换为小时用于计算
                current_time_hr = current_time_min / 60.0
                auxiliary_time_hr = auxiliary_time_min / 60.0
                
                gap += (auxiliary_time_hr - current_time_hr) * (auxiliary_flows[link_id] - current_flows[link_id])
            
            relative_gap = abs(gap) / max(1.0, total_demand)
            
            # 计算总出行时间（车·小时）
            total_travel_time = 0.0
            for link_id, flow in current_flows.items():
                link = network.links[link_id]
                travel_time_min = link.get_travel_time(flow)  # 分钟
                travel_time_hr = travel_time_min / 60.0       # 小时
                total_travel_time += flow * travel_time_hr    # 车·小时
            
            iteration_log.append({
                'iteration': iteration + 1,
                'relative_gap': relative_gap,
                'total_time': total_travel_time,
                'step_size': optimal_alpha
            })
            
            print(f"迭代 {iteration + 1}: 相对间隙 = {relative_gap:.6f}, "
                  f"总时间 = {total_travel_time * 60:.2f} 车·小时, "
                  f"步长 = {optimal_alpha:.4f}")
            
            # 检查收敛条件
            if relative_gap < tolerance:
                print(f"在第 {iteration + 1} 次迭代达到收敛")
                break
            
            # 检查步长是否过小导致停滞
            if optimal_alpha < 1e-5 and iteration > 10:
                print(f"步长过小({optimal_alpha:.6f})，算法可能停滞，提前结束")
                break
        
        print(f"最终相对间隙: {relative_gap:.6f}, 目标收敛阈值: {tolerance}")
        
        return current_flows, iteration_log

    @staticmethod
    def calculate_total_travel_time(network: Network, flows: Dict[int, float]) -> float:
        """
        计算总出行时间，单位：车·小时
        
        Args:
            network: 网络对象
            flows: 路段流量字典
        
        Returns:
            总出行时间（车·小时）
        """
        total_time = 0.0
        for link_id, flow in flows.items():
            if link_id in network.links:
                link = network.links[link_id]
                travel_time_min = link.get_travel_time(flow)  # 分钟
                travel_time_hr = travel_time_min / 60.0       # 转换为小时
                total_time += flow * travel_time_hr          # 车·小时
        
        return total_time
    
    @staticmethod
    def calculate_average_travel_time(network: Network, flows: Dict[int, float], 
                                     total_demand: float) -> float:
        """
        计算平均出行时间，单位：小时/车
        
        Args:
            network: 网络对象
            flows: 路段流量字典
            total_demand: 总需求
        
        Returns:
            平均出行时间（小时/车）
        """
        if total_demand <= 0:
            return 0.0
        
        total_time = AssignmentAlgorithms.calculate_total_travel_time(network, flows)
        return total_time / total_demand