# 失败类型统计

- 缺失或不完整: 234
- 数值错误: 1217
- 全局覆盖或非 JSON: 62
- 未知: 0

## 示例

### 缺失或不完整
- u=0.1, n=8, p=uniform, trial=1: {"task_001": "9CFF_100_LAV", "task_002": "E73A_200_LAV", "task_004": "C078_400_LAV", "task_005": "32B5_500_LAV_ERR", "task_006": "F4EF_600_LAV", "task_007": "EDB1_700_LAV", "task_0
- u=0.1, n=16, p=front, trial=5: {"task_001": "E3AE_100_LAV", "task_002": "A5DD_200_LAV", "task_003": "A51B_300_LAV", "task_004": "AF6E_400_LAV", "task_005": "90D2_500_LAV", "task_006": "3E5E_600_LAV", "task_007":
- u=0.1, n=32, p=front, trial=4: {"task_001": "159F_100_LAV_ERR", "task_002": "FA3A_200_LAV", "task_004": "0D3E_400_LAV", "task_005": "6833_500_LAV_ERR", "task_006": "0A4E_600_LAV_ERR", "task_007": "47A8_700_LAV_E

### 数值错误
- u=0.1, n=4, p=edges, trial=1: {"task_001": "C7EF_100_LAV", "task_002": "29D7_200_LAV", "task_003": "2786_300_LAV_ERR", "task_004": "4306_400_LAV"}
- u=0.1, n=4, p=edges, trial=3: {"task_001": "4B83_100_LAV_ERR", "task_002": "2EF7_200_LAV", "task_003": "15EA_300_LAV", "task_004": "089C_400_LAV"}
- u=0.1, n=4, p=edges, trial=7: {"task_001": "1C6E_100_LAV", "task_002": "61F2_200_LAV", "task_003": "A8E0_300_LAV", "task_004": "1180_400_LAV_ERR"}

### 全局覆盖或非 JSON
- u=0.55, n=48, p=edges, trial=4: 非 JSON 响应
- u=0.7, n=48, p=uniform, trial=4: 非 JSON 响应
- u=0.7, n=64, p=front, trial=6: 非 JSON 响应

### 未知
- （无样本）

