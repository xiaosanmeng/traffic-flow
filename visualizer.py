"""
visualizer.py - 可视化模块（使用节点坐标）
"""

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from typing import Dict, List, Tuple
from network import Network

class Visualizer:
    """可视化类"""
    
    @staticmethod
    def plot_network(
        network: Network, 
        link_flows: Dict[int, float] = None,
        title: str = "交通网络流量分配图",
        save_path: str = None,
        show_node_names: bool = True,
        show_link_flows: bool = True
    ):
        """
        绘制路网流量图（使用节点坐标）
        """
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # 获取节点位置
        node_positions = {}
        for node_id, node in network.nodes.items():
            node_positions[node_id] = (node.x, node.y)
        
        # 绘制路段
        max_flow = max(link_flows.values()) if link_flows and link_flows.values() else 1
        min_flow = min(link_flows.values()) if link_flows and link_flows.values() else 0
        
        # 只绘制原始路段（ID小于1000的），避免重复绘制双向路段
        drawn_links = set()
        
        for link_id, link in network.links.items():
            # 只绘制原始路段
            if link_id >= 1000:
                continue
            
            from_pos = node_positions[link.from_node]
            to_pos = node_positions[link.to_node]
            
            # 检查是否已经绘制过反向
            reverse_key = (link.to_name, link.from_name)
            if reverse_key in drawn_links:
                # 调整绘制位置以避免重叠
                offset = 0.8
            else:
                offset = 0
                drawn_links.add((link.from_name, link.to_name))
            
            # 计算箭头位置（考虑偏移）
            dx = to_pos[0] - from_pos[0]
            dy = to_pos[1] - from_pos[1]
            
            # 归一化
            length = np.sqrt(dx*dx + dy*dy)
            if length > 0:
                dx, dy = dx/length, dy/length
            
            # 垂直方向偏移量
            perp_dx = -dy * 0.5 * offset
            perp_dy = dx * 0.5 * offset
            
            # 起点和终点（考虑偏移）
            start_x = from_pos[0] + perp_dx
            start_y = from_pos[1] + perp_dy
            end_x = to_pos[0] + perp_dx
            end_y = to_pos[1] + perp_dy
            
            # 线宽和颜色基于流量
            if link_flows:
                flow = link_flows.get(link_id, 0)
                # 归一化流量用于颜色映射
                if max_flow > min_flow:
                    normalized_flow = (flow - min_flow) / (max_flow - min_flow)
                else:
                    normalized_flow = 0.5
                
                # 使用颜色映射
                color = cm.RdYlBu_r(normalized_flow)
                
                # 线宽与流量成正比
                linewidth = 1 + 5 * normalized_flow
                
                # 绘制带箭头的线
                arrow = ax.annotate('', 
                           xy=(end_x, end_y), 
                           xytext=(start_x, start_y),
                           arrowprops=dict(arrowstyle='->', 
                                         color=color, 
                                         lw=linewidth,
                                         alpha=0.8,
                                         shrinkA=5, shrinkB=5))
                
                # 标注流量
                if show_link_flows and flow > 0.1:
                    mid_x = (start_x + end_x) / 2 + perp_dx * 0.5
                    mid_y = (start_y + end_y) / 2 + perp_dy * 0.5
                    
                    # 计算角度
                    angle = np.degrees(np.arctan2(dy, dx))
                    
                    ax.text(mid_x, mid_y, 
                           f'{flow:.0f}', 
                           fontsize=9, 
                           ha='center', va='center',
                           rotation=angle if abs(angle) < 90 else angle + 180,
                           bbox=dict(boxstyle='round,pad=0.2', 
                                   facecolor='white', 
                                   alpha=0.8))
                
                # 在箭头旁边标注路段名称
                name_x = (start_x + end_x) / 2 + perp_dx * 1.5
                name_y = (start_y + end_y) / 2 + perp_dy * 1.5
                
                ax.text(name_x, name_y, 
                       f'{link.from_name}{link.to_name}',
                       fontsize=8, ha='center', va='center',
                       color='darkblue', alpha=0.7)
            else:
                # 无流量信息，绘制基本网络
                ax.plot([start_x, end_x], [start_y, end_y], 
                       'k-', alpha=0.5, linewidth=1)
        
        # 绘制节点
        for node_id, pos in node_positions.items():
            node = network.nodes[node_id]
            ax.plot(pos[0], pos[1], 'o', markersize=20, 
                   markerfacecolor='lightblue', 
                   markeredgecolor='black',
                   markeredgewidth=2)
            
            if show_node_names:
                ax.text(pos[0], pos[1], node.name, 
                       fontsize=14, ha='center', va='center', 
                       fontweight='bold')
        
        # 添加颜色条
        if link_flows and max_flow > 0:
            sm = plt.cm.ScalarMappable(cmap=cm.RdYlBu_r, 
                                      norm=plt.Normalize(vmin=min_flow, 
                                                       vmax=max_flow))
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
            cbar.set_label('路段流量 (veh/h)', fontsize=12)
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('X 坐标 (km)', fontsize=12)
        ax.set_ylabel('Y 坐标 (km)', fontsize=12)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_aspect('equal')
        
        # 设置坐标轴范围
        all_x = [node.x for node in network.nodes.values()]
        all_y = [node.y for node in network.nodes.values()]
        ax.set_xlim(min(all_x) - 2, max(all_x) + 2)
        ax.set_ylim(min(all_y) - 2, max(all_y) + 2)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"网络图已保存到: {save_path}")
        
        return fig, ax
    
    @staticmethod
    def plot_convergence(iteration_log: List[Dict], 
                        save_path: str = None):
        """绘制收敛曲线"""
        if not iteration_log:
            return
        
        iterations = [log['iteration'] for log in iteration_log]
        gaps = [log['relative_gap'] for log in iteration_log]
        times = [log['total_time'] for log in iteration_log]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 绘制相对间隙
        ax1.semilogy(iterations, gaps, 'b-o', linewidth=2, markersize=6)
        ax1.set_xlabel('迭代次数', fontsize=12)
        ax1.set_ylabel('相对间隙 (log scale)', fontsize=12)
        ax1.set_title('Frank-Wolfe算法收敛曲线', fontsize=14)
        ax1.grid(True, alpha=0.3)
        
        # 绘制总出行时间
        ax2.plot(iterations, times, 'r-s', linewidth=2, markersize=6)
        ax2.set_xlabel('迭代次数', fontsize=12)
        ax2.set_ylabel('总出行时间 (veh·min)', fontsize=12)
        ax2.set_title('总出行时间变化', fontsize=14)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"收敛曲线已保存到: {save_path}")
        
        return fig, (ax1, ax2)