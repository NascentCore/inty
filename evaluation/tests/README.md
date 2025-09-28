# Evaluation Tests

这个目录包含 evaluation 系统的所有测试文件，使用 [Vitest](https://vitest.dev/guide/) 测试框架。

## 运行测试

### 1. 运行所有测试 (监听模式)
```bash
cd evaluation
npm run test
```

### 2. 运行所有测试 (一次性)
```bash
cd evaluation
npm run test:run
```

### 3. 运行特定测试文件
```bash
npx vitest run tests/test_agent_extensions.test.ts
```
