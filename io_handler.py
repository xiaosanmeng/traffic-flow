"""
io_handler.py - JSON格式输入输出处理模块
"""

import pandas as pd
import numpy as np
import json
import math
from typing import Dict, Tuple
from network import Network, Link, Node

class IOHandler:
    """文件读写处理器"""
    
    @staticmethod
    def read_network_json(file_path: str) -> Network:
        """
        读取JSON格式的路网文件
        格式：包含nodes和links的信息
        """
        network = Network()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"成功读取路网文件: {file_path}")
            
            # 读取节点信息
            nodes_data = data.get('nodes', {})
            node_names = nodes_data.get('name', [])
            node_x = nodes_data.get('x', [])
            node_y = nodes_data.get('y', [])
            
            print(f"节点数量: {len(node_names)}")
            
            # 创建节点
            for i, name in enumerate(node_names):
                node = Node(
                    id=i + 1,  # 从1开始
                    name=name,
                    x=float(node_x[i]),
                    y=float(node_y[i])
                )
                network.add_node(node)
            
            # 读取路段信息
            links_data = data.get('links', {})
            between = links_data.get('between', [])
            capacities = links_data.get('capacity', [])
            max_speeds = links_data.get('speedmax', [])
            
            print(f"路段数量: {len(between)}")
            
            # 创建路段
            for i, link_str in enumerate(between):
                # 检查路段字符串是否有效（两端节点是否存在）
                if len(link_str) >= 2:
                    from_name = link_str[0]
                    to_name = link_str[1]
                    
                    from_node = network.get_node_id_by_name(from_name)
                    to_node = network.get_node_id_by_name(to_name)
                    
                    if from_node is None or to_node is None:
                        print(f"警告: 无法找到节点 {from_name} 或 {to_name}")
                        continue
                    
                    # 计算路段长度（使用节点坐标）
                    node1 = network.nodes[from_node]
                    node2 = network.nodes[to_node]
                    dx = node2.x - node1.x
                    dy = node2.y - node1.y
                    length = math.sqrt(dx*dx + dy*dy)  # 千米
                    print(f"路段 {i+1}: {from_name} -> {to_name}, 长度: {length:.2f}千米")
                    
                    # 自由流行程时间 t0 = length / max_speed (小时)
                    max_speed = float(max_speeds[i])  # 千米/小时
                    if max_speed > 0:
                        free_flow_time = length / max_speed  # 小时
                    else:
                        free_flow_time = 0
                    
                    link = Link(
                        id=i + 1,  # 从1开始
                        from_node=from_node,
                        to_node=to_node,
                        from_name=from_name,
                        to_name=to_name,
                        length=length,
                        free_flow_time=free_flow_time,
                        capacity=float(capacities[i]),
                        max_speed=max_speed,
                        is_bidirectional=True  # 根据问题描述，所有路段为双向
                    )
                    
                    network.add_link(link)
            
            # print(f"网络构建完成，总路段数（包括双向）: {len(network.links)}")
            
        except Exception as e:
            print(f"读取路网文件失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return network
    
    @staticmethod
    def read_demand_json(file_path: str) -> Dict[Tuple[str, str], float]:
        """
        读取JSON格式的出行需求文件
        格式：包含from, to, amount
        """
        od_matrix = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"成功读取需求文件: {file_path}")
            
            from_nodes = data.get('from', [])
            to_nodes = data.get('to', [])
            amounts = data.get('amount', [])
            
            total_demand = 0
            for i in range(len(from_nodes)):
                origin = from_nodes[i]
                destination = to_nodes[i]
                demand = float(amounts[i])
                od_matrix[(origin, destination)] = demand
                total_demand += demand
            
            print(f"OD对数量: {len(od_matrix)}")
            print(f"总出行需求量: {total_demand} 辆/小时")
            
        except Exception as e:
            print(f"读取需求文件失败: {e}")
            raise
        
        return od_matrix
    
    @staticmethod
    def save_results(
        network: Network, 
        link_flows: Dict[int, float], 
        file_path: str
    ) -> pd.DataFrame:
        """
        保存分配结果到CSV文件
        """
        results = []
        
        for link_id, flow in link_flows.items():
            link = network.links[link_id]
            
            # # 合并反向路段
            # if link_id >= 1000:
            #     continue
            
            travel_time = 60 * link.get_travel_time(flow) 
            volume_capacity_ratio = flow / link.capacity if link.capacity > 0 else 0
            
            results.append({
                'link_id': link_id,
                'from_node': link.from_name,
                'to_node': link.to_name,
                'length_km': link.length,
                'max_speed_kmh': link.max_speed,
                'free_flow_time_min': link.free_flow_time * 60,  # 转换为分钟
                'capacity_veh_h': link.capacity,
                'flow_veh_h': flow,
                'v_c_ratio': volume_capacity_ratio,
                'travel_time': travel_time,  # 已经是分钟
                'additional_delay_min': travel_time - (link.free_flow_time * 60)
            })
        
        df = pd.DataFrame(results)
        df.to_csv(file_path, index=False)
        print(f"分配结果已保存到: {file_path}")
        
        # 打印汇总统计
        if len(results) > 0:
            total_flow = df['flow_veh_h'].sum()
            avg_vc = df['v_c_ratio'].mean()
            max_vc = df['v_c_ratio'].max()
            
            print(f"总流量: {total_flow:.1f} 辆/小时")
            print(f"平均V/C比: {avg_vc:.3f}")
            print(f"最大V/C比: {max_vc:.3f}")
        
        return df
    
    # @staticmethod
    # def create_example_files():
    #     # 格式化输出
    #     print("\n节点坐标（千米）:")
    #     print("名称  X坐标  Y坐标")
    #     for i in range(len(network_data["nodes"]["name"])):
    #         name = network_data["nodes"]["name"][i]
    #         x = network_data["nodes"]["x"][i]
    #         y = network_data["nodes"]["y"][i]
    #         print(f"{name:2}    {x:5.1f}  {y:5.1f}")
        
    #     print("\n路段信息:")
    #     print("路段  通行能力(辆/小时)  最大限速(千米/小时)")
    #     for i in range(len(network_data["links"]["between"])):
    #         between = network_data["links"]["between"][i]
    #         capacity = network_data["links"]["capacity"][i]
    #         speed = network_data["links"]["speedmax"][i]
    #         print(f"{between:4}    {capacity:10}        {speed:10}")
        
    #     print("\n出行需求:")
    #     print("起点  迄点  交通量(辆/小时)")
    #     for i in range(len(demand_data["from"])):
    #         origin = demand_data["from"][i]
    #         dest = demand_data["to"][i]
    #         amount = demand_data["amount"][i]
    #         print(f"{origin:2}    {dest:2}    {amount:10}")
        
    #     return network_data, demand_data
