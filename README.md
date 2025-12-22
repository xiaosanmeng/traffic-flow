# 交通流优化器 (TrafficFlow Optimizer)

一个用于交通分配计算的Python软件，支持多种交通分配算法和结果可视化。

## 功能

1. **数据读取**：支持CSV格式的路网文件和出行需求文件
2. **分配算法**：
   - 全有全无分配 (All-or-Nothing)
   - 增量分配 (Incremental Assignment)
   - 用户均衡分配 (User Equilibrium - Frank-Wolfe算法)
3. **结果评估**：
   - 计算路网总出行时间
   - 计算路段饱和度 (V/C比)
   - 识别拥堵路段
4. **可视化**：
   - 绘制路网流量图
   - 颜色编码显示流量大小
   - 收敛曲线可视化

