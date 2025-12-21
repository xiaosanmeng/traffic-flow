"""
network.py - 路网数据结构模块
"""

import numpy as np
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class Node:
    """节点类"""
    id: int
    name: str
    x: float
    y: float

@dataclass
class Link:
    """路段类"""
    id: int
    from_node: int
    to_node: int
    from_name: str
    to_name: str
    length: float
    free_flow_time: float  # 自由流行程时间 t0（小时）
    capacity: float # 单向通行能力
    max_speed: float
    is_bidirectional: bool = True  # 是否为双向
    
    def get_travel_time(self, flow: float) -> float:
        """
        根据给定的行程时间函数计算行程时间(小时)
        t(q) = t0 * (1 + q/capacity)^2
        其中 t0 = length / max_speed
        """
        # # 计算自由流行程时间
        # if self.max_speed > 0:
        #     t0 = self.length / self.max_speed  # 小时
        #     # 转换为分钟便于显示
        #     t0_minutes = t0 * 60
        # else:
        #     t0_minutes = self.free_flow_time
        
        # 使用给定的行程时间函数
        if self.capacity > 0:
            return self.free_flow_time * (1.0 + flow / self.capacity) ** 2
        else:
            return self.free_flow_time

class Network:
    """交通网络类"""
    
    def __init__(self):
        self.nodes = {}  # node_id -> Node对象
        self.node_name_to_id = {}  # 节点名称到ID的映射
        self.links = {}  # link_id -> Link对象
        self.adjacency = {}  # from_node -> [(to_node, link_id), ...]   正向邻接表
        self.reverse_adjacency = {}  # to_node -> [(from_node, link_id), ...]  反向邻接表   
        
    def add_node(self, node: Node):
        """添加节点"""
        self.nodes[node.id] = node
        self.node_name_to_id[node.name] = node.id
    
    def add_link(self, link: Link):
        """添加路段"""
        self.links[link.id] = link
        
        # 更新邻接表（正向）
        if link.from_node not in self.adjacency:
            self.adjacency[link.from_node] = []
        self.adjacency[link.from_node].append((link.to_node, link.id))
        
        # 如果是双向路段，添加反向连接
        if link.is_bidirectional:
            # 创建反向路段（新ID）
            reverse_link_id = link.id * 1000  # 使用大数区分
            reverse_link = Link(
                id=reverse_link_id,
                from_node=link.to_node,
                to_node=link.from_node,
                from_name=link.to_name,
                to_name=link.from_name,
                length=link.length,
                free_flow_time=link.free_flow_time,
                capacity=link.capacity,
                max_speed=link.max_speed,
                is_bidirectional=True
            )
            self.links[reverse_link_id] = reverse_link
            
            # 更新反向连接的邻接表
            if link.to_node not in self.adjacency:
                self.adjacency[link.to_node] = []
            self.adjacency[link.to_node].append((link.from_node, reverse_link_id))
        
        # 更新反向邻接表（用于反向搜索）
        if link.to_node not in self.reverse_adjacency:
            self.reverse_adjacency[link.to_node] = []
        self.reverse_adjacency[link.to_node].append((link.from_node, link.id))
        
        # 反向路段的反向邻接表
        if link.is_bidirectional:
            if link.from_node not in self.reverse_adjacency:
                self.reverse_adjacency[link.from_node] = []
            self.reverse_adjacency[link.from_node].append((link.to_node, reverse_link_id))
    
    def get_node_id_by_name(self, name: str) -> Optional[int]:
        """根据节点名称获取节点ID"""
        return self.node_name_to_id.get(name)
    
    def get_node_name_by_id(self, node_id: int) -> Optional[str]:
        """根据节点ID获取节点名称"""
        node = self.nodes.get(node_id)
        return node.name if node else None
    
    def get_link(self, from_node: int, to_node: int) -> Optional[Link]:
        """获取两点间的路段"""
        if from_node in self.adjacency:
            for node, link_id in self.adjacency[from_node]:
                if node == to_node:
                    return self.links[link_id]
        return None
    
    def get_link_by_names(self, from_name: str, to_name: str) -> Optional[Link]:
        """根据节点名称获取路段"""
        from_node = self.get_node_id_by_name(from_name)
        to_node = self.get_node_id_by_name(to_name)
        if from_node is not None and to_node is not None:
            return self.get_link(from_node, to_node)
        return None
    
    def get_outgoing_links(self, node: int) -> List[Link]:
        """获取从节点出发的所有路段"""
        if node not in self.adjacency:
            return []
        return [self.links[link_id] for _, link_id in self.adjacency[node]]
    
    def get_incoming_links(self, node: int) -> List[Link]:
        """获取进入节点的所有路段"""
        if node not in self.reverse_adjacency:
            return []
        return [self.links[link_id] for _, link_id in self.reverse_adjacency[node]]
    
    def get_shortest_path(self, origin: int, destination: int, 
                         flows: Dict[int, float] = None) -> Tuple[List[int], float]:
        """
        使用Dijkstra算法计算最短路径
        flows: 当前路段流量，如果不提供则使用自由流时间
        """
        if flows is None:
            flows = {link_id: 0 for link_id in self.links}
        
        # 初始化距离和前驱节点
        dist = {node_id: float('inf') for node_id in self.nodes}
        prev = {node_id: None for node_id in self.nodes}
        dist[origin] = 0
        
        # 未访问节点集合
        unvisited = set(self.nodes.keys())
        
        while unvisited:
            # 选择当前距离最小的节点
            current = min(unvisited, key=lambda node: dist[node])
            
            # 如果找到终点，提前结束
            if current == destination:
                break
            
            unvisited.remove(current)
            
            # 更新邻居节点的距离
            if current in self.adjacency:
                # 遍历当前节点的所有邻居节点
                for neighbor, link_id in self.adjacency[current]:
                    if neighbor in unvisited:
                        link = self.links[link_id]
                        travel_time = link.get_travel_time(flows.get(link_id, 0))
                        new_dist = dist[current] + travel_time
                        
                        if new_dist < dist[neighbor]:
                            dist[neighbor] = new_dist
                            prev[neighbor] = current
        
        # 重建路径
        if dist[destination] == float('inf'):
            return [], float('inf')
        
        path = []
        current = destination   # 从终点开始沿前驱节点构建路径
        
        while current != origin:
            if prev[current] is None:
                return [], float('inf')
            
            prev_node = prev[current]
            path.insert(0, current) # 插入当前节点到路径开头
            current = prev_node
        
        path.insert(0, origin)
        return path, dist[destination]
    
    def get_shortest_path_by_names(self, origin_name: str, destination_name: str,
                                 flows: Dict[int, float] = None) -> Tuple[List[str], float]:
        """根据节点名称计算最短路径"""
        origin = self.get_node_id_by_name(origin_name)
        destination = self.get_node_id_by_name(destination_name)
        
        if origin is None or destination is None:
            return [], float('inf')
        
        path, cost = self.get_shortest_path(origin, destination, flows)
        
        # 将节点ID转换为名称
        path_names = [self.get_node_name_by_id(node_id) for node_id in path]
        return path_names, cost
    
    def get_all_shortest_paths(self, origin: int, destination: int, 
                              max_paths: int = 10) -> List[Tuple[List[int], float]]:
        """获取多条最短路径（K短路算法简化版）"""
        paths = []
        
        # 主路径
        main_path, main_cost = self.get_shortest_path(origin, destination)
        if main_path:
            paths.append((main_path, main_cost))
        
        # 简单实现：依次移除路径中的一条边，重新计算
        for i in range(len(main_path) - 1):
            from_node = main_path[i]
            to_node = main_path[i + 1]
            
            # 临时移除边
            link = self.get_link(from_node, to_node)
            if not link:
                continue
            
            # 备份并移除
            backup_links = []
            for node, link_id in list(self.adjacency[from_node]):
                if node == to_node:
                    backup_links.append((from_node, to_node, link_id))
                    self.adjacency[from_node].remove((node, link_id))
            
            # 计算新路径
            new_path, new_cost = self.get_shortest_path(origin, destination)
            if new_path and new_path not in [p[0] for p in paths]:
                paths.append((new_path, new_cost))
            
            # 恢复边
            for from_node, to_node, link_id in backup_links:
                self.adjacency[from_node].append((to_node, link_id))
            
            if len(paths) >= max_paths:
                break
        
        return paths
    
    def calculate_distance(self, node1_id: int, node2_id: int) -> float:
        """计算两个节点之间的欧几里得距离"""
        node1 = self.nodes[node1_id]
        node2 = self.nodes[node2_id]
        dx = node2.x - node1.x
        dy = node2.y - node1.y
        return math.sqrt(dx*dx + dy*dy)