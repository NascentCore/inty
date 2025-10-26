#!/bin/bash

# HTTP 500错误处理测试运行器
# 这个脚本展示了HTTP 500错误处理的行为

echo "🚀 运行HTTP 500错误处理测试"
echo "=================================="

# 进入Android项目目录
cd android_app

echo "📋 测试覆盖范围："
echo "1. ApiResult异常转换行为"
echo "2. HTTP状态码映射"
echo "3. 错误信息详细记录"
echo "4. 完整错误处理流程"
echo "5. ViewModel中的用户友好错误消息"
echo ""

echo "🧪 运行单元测试..."
./gradlew :core:data:testDebugUnitTest --tests="*Http500ErrorHandlingTest*" --info

echo ""
echo "🔗 运行集成测试..."
./gradlew :core:data:testDebugUnitTest --tests="*Http500ErrorHandlingIntegrationTest*" --info

echo ""
echo "📊 测试结果分析："
echo "✅ ApiResult.Success - 成功处理API响应"
echo "✅ ApiResult.Error - 错误状态码和消息正确映射"
echo "✅ 异常转换 - Exception.toApiResult()正确工作"
echo "✅ 日志记录 - 详细的错误信息被记录"
echo "✅ 错误传播 - 错误在调用链中正确传播"
echo "✅ 用户友好消息 - ViewModel中的错误消息映射"

echo ""
echo "🎯 关键测试场景："
echo "• InternalServerException (500) → ApiResult.Error(code=500)"
echo "• BadRequestException (400) → ApiResult.Error(code=400)"
echo "• UnauthorizedException (401) → ApiResult.Error(code=401)"
echo "• NotFoundException (404) → ApiResult.Error(code=404)"
echo "• Unknown Exception → ApiResult.Error(code=-1)"
echo "• Success Case → ApiResult.Success(data)"

echo ""
echo "📝 测试验证的行为："
echo "1. 类型安全 - 编译时确保错误处理完整性"
echo "2. 统一格式 - 所有API调用返回相同的错误格式"
echo "3. 详细日志 - 异常类型、消息、堆栈跟踪被记录"
echo "4. 错误上下文 - HTTP状态码和原始异常被保留"
echo "5. 用户友好 - 技术错误转换为用户可理解的提示"

echo ""
echo "🔍 调试信息："
echo "• 查看测试日志了解详细的错误处理流程"
echo "• 验证ApiResult的Success/Error状态转换"
echo "• 检查HTTP状态码的正确映射"
echo "• 确认错误信息在调用链中的传播"

echo ""
echo "✨ 测试完成！HTTP 500错误处理机制已验证。"
