# Architecture Documentation

本目录保存长期稳定的系统架构说明。

## 文档职责

- 架构说明：解释系统边界和模块关系。
- decisions：记录关键技术决策。
- operations：记录运行和生产流程。
- technical：记录接口和领域设计。

## 原则

不要把历史执行过程、PR记录和临时任务放入架构文档。

架构文档回答：

- 系统为什么这样设计。
- 模块如何协作。
- 哪些边界不能突破。

具体实施记录进入对应 Issue、PR 或 Changelog。

## Composition Root 边界

- `platform-backend/app/main.py` 只装配 Router 与 Middleware，不承载业务规则。
- 风险敞口、EOD 策略和权限映射由各自模块显式导入，禁止运行时 monkey patch。
- 领域模块之间通过普通 import 建立可静态分析的依赖，不依赖启动顺序改变函数实现。
- 同一业务事实只能有一个权威实现；残余敞口计算统一由 `execution_exposure.py` 提供。
- `tests/test_architecture_boundaries.py` 对上述边界进行静态回归检查。
