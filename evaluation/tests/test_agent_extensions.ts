/**
 * 测试 Agent Extensions 功能
 * 验证头像截取数据在 extensions 字段中的存储和读取
 */

import { Agent, AvatarCropData } from '../types';

// 模拟 API 调用
const API_BASE_URL = 'http://localhost:8000';

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
}

/**
 * 获取智能体列表
 */
async function getAgents(): Promise<Agent[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/ai/agents/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // 注意：实际使用时需要添加 Authorization header
        // 'Authorization': 'Bearer YOUR_TOKEN'
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<Agent[]> = await response.json();
    return result.data || [];
  } catch (error) {
    console.error('获取智能体列表失败:', error);
    throw error;
  }
}

/**
 * 获取单个智能体详情
 */
async function getAgent(agentId: string): Promise<Agent | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/ai/agents/${agentId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // 注意：实际使用时需要添加 Authorization header
        // 'Authorization': 'Bearer YOUR_TOKEN'
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<Agent> = await response.json();
    return result.data;
  } catch (error) {
    console.error(`获取智能体 ${agentId} 失败:`, error);
    throw error;
  }
}

/**
 * 测试 extensions 字段中的头像截取数据
 */
async function testAgentExtensions() {
  console.log('🧪 开始测试 Agent Extensions 功能...\n');

  try {
    // 1. 获取智能体列表
    console.log('📋 获取智能体列表...');
    const agents = await getAgents();
    console.log(`✅ 成功获取 ${agents.length} 个智能体\n`);

    if (agents.length === 0) {
      console.log('⚠️  没有找到智能体，请先创建一些智能体进行测试');
      return;
    }

    // 2. 检查每个智能体的 extensions 字段
    console.log('🔍 检查智能体的 extensions 字段...\n');
    
    for (let i = 0; i < agents.length; i++) {
      const agent = agents[i];
      console.log(`--- 智能体 ${i + 1}: ${agent.name} (ID: ${agent.id}) ---`);
      
      // 检查 extensions 字段
      if (agent.extensions) {
        console.log('✅ 存在 extensions 字段');
        console.log('📄 Extensions 内容:', JSON.stringify(agent.extensions, null, 2));
        
        // 检查头像截取数据
        const avatarCrop = agent.extensions.avatar_crop as AvatarCropData | undefined;
        if (avatarCrop) {
          console.log('🎯 发现头像截取数据:');
          console.log(`   - 截取位置: (${avatarCrop.x}, ${avatarCrop.y})`);
          console.log(`   - 截取尺寸: ${avatarCrop.width} x ${avatarCrop.height}`);
          console.log(`   - 原始图片尺寸: ${avatarCrop.imageWidth} x ${avatarCrop.imageHeight}`);
          
          // 验证数据完整性
          const isValid = avatarCrop.x >= 0 && avatarCrop.y >= 0 && 
                         avatarCrop.width > 0 && avatarCrop.height > 0 &&
                         avatarCrop.imageWidth > 0 && avatarCrop.imageHeight > 0;
          console.log(`   - 数据有效性: ${isValid ? '✅ 有效' : '❌ 无效'}`);
        } else {
          console.log('ℹ️  没有头像截取数据');
        }
        
        // 检查其他扩展数据
        const otherExtensions = Object.keys(agent.extensions).filter(key => key !== 'avatar_crop');
        if (otherExtensions.length > 0) {
          console.log('📋 其他扩展数据:', otherExtensions.join(', '));
        }
      } else {
        console.log('ℹ️  没有 extensions 字段');
      }
      
      // 检查头像相关字段
      console.log('🖼️  头像信息:');
      console.log(`   - avatar: ${agent.avatar ? '✅ 存在' : '❌ 不存在'}`);
      console.log(`   - background: ${agent.background ? '✅ 存在' : '❌ 不存在'}`);
      
      console.log(''); // 空行分隔
    }

    // 3. 测试单个智能体详情获取
    if (agents.length > 0) {
      const firstAgent = agents[0];
      console.log(`🔍 测试获取单个智能体详情: ${firstAgent.name}...`);
      
      const agentDetail = await getAgent(firstAgent.id);
      if (agentDetail) {
        console.log('✅ 成功获取智能体详情');
        
        // 比较列表数据和详情数据的一致性
        const listExtensions = JSON.stringify(firstAgent.extensions);
        const detailExtensions = JSON.stringify(agentDetail.extensions);
        const isConsistent = listExtensions === detailExtensions;
        
        console.log(`📊 数据一致性: ${isConsistent ? '✅ 一致' : '❌ 不一致'}`);
        
        if (!isConsistent) {
          console.log('⚠️  列表和详情中的 extensions 数据不一致:');
          console.log('列表数据:', listExtensions);
          console.log('详情数据:', detailExtensions);
        }
      } else {
        console.log('❌ 获取智能体详情失败');
      }
    }

    console.log('\n🎉 Agent Extensions 测试完成!');

  } catch (error) {
    console.error('❌ 测试失败:', error);
  }
}

/**
 * 测试头像截取数据的计算逻辑
 */
function testAvatarCropCalculation() {
  console.log('\n🧮 测试头像截取数据计算逻辑...\n');
  
  // 模拟截取数据
  const mockCropData: AvatarCropData = {
    x: 100,
    y: 50,
    width: 200,
    height: 200,
    imageWidth: 800,
    imageHeight: 600
  };
  
  console.log('📐 模拟截取数据:', mockCropData);
  
  // 计算显示尺寸 (假设显示为 64x64 的圆形头像)
  const displaySize = 64;
  const scale = displaySize / mockCropData.width;
  
  const displayWidth = mockCropData.imageWidth * scale;
  const displayHeight = mockCropData.imageHeight * scale;
  const offsetX = -mockCropData.x * scale;
  const offsetY = -mockCropData.y * scale;
  
  console.log('🎨 显示计算结果:');
  console.log(`   - 缩放比例: ${scale.toFixed(3)}`);
  console.log(`   - 图片显示尺寸: ${displayWidth.toFixed(1)} x ${displayHeight.toFixed(1)}`);
  console.log(`   - 偏移量: (${offsetX.toFixed(1)}, ${offsetY.toFixed(1)})`);
  
  // 计算截取区域在原始图片中的百分比位置
  const cropLeftPercent = (mockCropData.x / mockCropData.imageWidth) * 100;
  const cropTopPercent = (mockCropData.y / mockCropData.imageHeight) * 100;
  const cropWidthPercent = (mockCropData.width / mockCropData.imageWidth) * 100;
  const cropHeightPercent = (mockCropData.height / mockCropData.imageHeight) * 100;
  
  console.log('📊 截取区域百分比:');
  console.log(`   - 位置: ${cropLeftPercent.toFixed(1)}%, ${cropTopPercent.toFixed(1)}%`);
  console.log(`   - 尺寸: ${cropWidthPercent.toFixed(1)}% x ${cropHeightPercent.toFixed(1)}%`);
}

// 运行测试
if (typeof window === 'undefined') {
  // Node.js 环境
  console.log('🚀 在 Node.js 环境中运行测试...\n');
  testAgentExtensions().then(() => {
    testAvatarCropCalculation();
  });
} else {
  // 浏览器环境
  console.log('🌐 在浏览器环境中运行测试...\n');
  // 可以通过浏览器控制台调用
  (window as any).testAgentExtensions = testAgentExtensions;
  (window as any).testAvatarCropCalculation = testAvatarCropCalculation;
  
  console.log('💡 提示: 在浏览器控制台中运行以下命令:');
  console.log('   testAgentExtensions()');
  console.log('   testAvatarCropCalculation()');
}

export { testAgentExtensions, testAvatarCropCalculation };
