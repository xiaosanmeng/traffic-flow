"""
evaluator.py - 分配结果评估模块
"""

import numpy as np
from typing import Dict, List, Tuple
from network import Network

class Evaluator:
    """评估类"""
    
    @staticmethod
    def calculate_total_travel_time(
        network: Network, 
        link_flows: Dict[int, float]
    ) -> float:
        """计算总出行时间（车·分钟）"""
        total_time = 0.0
        
        for link_id, flow in link_flows.items():
            # 只计算原始路段，避免重复计算双向路段
            if link_id >= 1000:
                continue
                
            link = network.links[link_id]
            travel_time = link.get_travel_time(flow)
            total_time += flow * travel_time
        
        return total_time
    
    @staticmethod
    def calculate_average_travel_time(
        network: Network, 
        link_flows: Dict[int, float], 
        total_demand: float
    ) -> float:
        """计算平均出行时间（分钟/车）"""
        total_time = Evaluator.calculate_total_travel_time(network, link_flows)
        
        if total_demand > 0:
            return total_time / total_demand
        return 0.0
    
    @staticmethod
    def calculate_volume_capacity_ratios(
        network: Network, 
        link_flows: Dict[int, float]
    ) -> Dict[str, float]:
        """计算路段饱和度（V/C比）"""
        vc_ratios = {}
        
        for link_id, flow in link_flows.items():
            # 双向合并计算
            if link_id >= 1000:
                continue
                
            link = network.links[link_id]
            if link.capacity > 0:
                key = f"{link.from_name}{link.to_name}" # 双向
                vc_ratios[key] = (flow + link_flows.get(link_id + 1000, 0)) / link.capacity
        
        return vc_ratios
    
    @staticmethod
    def find_congested_links(
        network: Network, 
        link_flows: Dict[int, float], 
        threshold: float = 0.8
    ) -> List[Tuple[str, float, float, str]]:
        """找出拥堵路段（V/C比超过阈值）"""
        congested_links = []
        vc_ratios = Evaluator.calculate_volume_capacity_ratios(network, link_flows)
        
        for link_key, vc_ratio in vc_ratios.items():
            if vc_ratio >= threshold:
                # 查找对应的link对象
                for link_id, link in network.links.items():
                    if link_id < 1000 and f"{link.from_name}{link.to_name}" == link_key:
                        congested_links.append((
                            link_key,
                            link_flows[link_id],
                            vc_ratio,
                            f"{link.from_name}->{link.to_name}"
                        ))
                        break
        
        # 按拥堵程度排序
        congested_links.sort(key=lambda x: x[2], reverse=True)
        
        return congested_links
    
    @staticmethod
    def compare_algorithms(
        network: Network,
        od_matrix: Dict[Tuple[str, str], float],
        algorithms_results: Dict[str, Dict[int, float]]
    ) -> Dict[str, Dict]:
        """比较不同算法的结果"""
        comparison = {}
        total_demand = sum(od_matrix.values())
        
        for algo_name, flows in algorithms_results.items():
            total_time = Evaluator.calculate_total_travel_time(network, flows)
            avg_time = Evaluator.calculate_average_travel_time(network, flows, total_demand)
            vc_ratios = Evaluator.calculate_volume_capacity_ratios(network, flows)
            
            # 计算统计指标
            if vc_ratios:
                max_vc = max(vc_ratios.values())
                avg_vc = np.mean(list(vc_ratios.values()))
                congested_count = len([v for v in vc_ratios.values() if v >= 0.8])
            else:
                max_vc = 0
                avg_vc = 0
                congested_count = 0
            
            comparison[algo_name] = {
                'total_travel_time': total_time,
                'average_travel_time': avg_time,
                'max_vc_ratio': max_vc,
                'average_vc_ratio': avg_vc,
                'congested_links_count': congested_count,
                'total_demand': total_demand
            }
        
        return comparison
    
    @staticmethod
    def print_comparison_table(comparison: Dict[str, Dict]):
        """打印算法比较表格"""
        print("\n" + "="*80)
        print("算法性能比较")
        print("="*80)
        
        headers = ["算法", "总出行时间(车·分钟)", "平均出行时间(分钟)", 
                  "最大V/C比", "平均V/C比", "拥堵路段数(V/C≥0.8)"]
        print(f"{headers[0]:<15} {headers[1]:<20} {headers[2]:<18} "
              f"{headers[3]:<12} {headers[4]:<12} {headers[5]:<15}")
        print("-"*80)
        
        for algo_name, metrics in comparison.items():
            print(f"{algo_name:<15} "
                  f"{metrics['total_travel_time']:<20.2f} "
                  f"{metrics['average_travel_time']:<18.2f} "
                  f"{metrics['max_vc_ratio']:<12.3f} "
                  f"{metrics['average_vc_ratio']:<12.3f} "
                  f"{metrics['congested_links_count']:<15}")
        
        print("="*80)
    
    @staticmethod
    def print_link_flow_details(network: Network, link_flows: Dict[int, float]):
        """打印路段流量详情"""
        print("\n路段流量详情:")
        print("-"*80)
        print("路段   流量(veh/h)   容量(veh/h)  V/C比   行程时间(min)   自由流时间(min)")
        # print("-"*80)
        
        total_flow = 0
        
        for link_id, flow in link_flows.items():
            # 双向合并
            if link_id >= 1000:
                continue
                
            link = network.links[link_id]
            travel_time = link.get_travel_time(flow)
            free_flow_time_min = link.free_flow_time * 60
            vc_ratio = flow / link.capacity if link.capacity > 0 else 0
            
            print(f"{link.from_name}{link.to_name}     "
                  f"{flow:^11.1f}   {link.capacity:<11.1f}   "
                  f"{vc_ratio:<5.3f}   {travel_time:<13.2f}   "
                  f"{free_flow_time_min:<13.2f}")
            
            total_flow += flow + link_flows[link_id + 1000]
        
        print("-"*80)
        print(f"总计    {total_flow:<12.1f} ")