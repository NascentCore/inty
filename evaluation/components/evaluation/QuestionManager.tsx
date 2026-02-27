/**
 * 问题管理组件
 * 负责测试问题的添加、编辑、导入、管理
 */

import React, { useState, useCallback } from "react";
import {
  Card,
  Button,
  Input,
  Upload,
  List,
  Tag,
  Space,
  Select,
  message,
  Modal,
  Alert,
  Tooltip,
  Popconfirm,
} from "antd";
import {
  UploadOutlined,
  DeleteOutlined,
  PlusOutlined,
  ClearOutlined,
  FileTextOutlined,
  EyeOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import type { UploadFile } from "antd";
import api from "../../services/api";
import type { QuestionFileUpload } from "../../types";
import { useJsonDisplay } from "../../hooks/useJsonDisplay";
import { JsonDisplayModal } from "../common/JsonDisplayModal";

const { Option } = Select;

interface QuestionManagerProps {
  questions: string[];
  onChange: (questions: string[]) => void;
  maxQuestions?: number;
}

interface QuestionSet {
  name: string;
  questions: string[];
}

export const QuestionManager: React.FC<QuestionManagerProps> = ({
  questions,
  onChange,
  maxQuestions = 50,
}) => {
  // 状态管理
  const [newQuestion, setNewQuestion] = useState("");
  const [savedQuestionSets, setSavedQuestionSets] = useState<QuestionSet[]>([]);
  const [uploading, setUploading] = useState(false);

  // JSON显示功能
  const { jsonModalVisible, jsonData, showJson, hideJson } = useJsonDisplay();

  // 加载保存的问题集
  React.useEffect(() => {
    try {
      const saved = localStorage.getItem("questionSets");
      if (saved) {
        setSavedQuestionSets(JSON.parse(saved));
      }
    } catch (error) {
      console.error("加载问题集失败:", error);
    }
  }, []);

  // 添加问题
  const addQuestion = useCallback(() => {
    const trimmedQuestion = newQuestion.trim();

    if (!trimmedQuestion) {
      message.warning("请输入问题内容");
      return;
    }

    if (questions.includes(trimmedQuestion)) {
      message.warning("问题已存在");
      return;
    }

    if (questions.length >= maxQuestions) {
      message.warning(`最多只能添加${maxQuestions}个问题`);
      return;
    }

    onChange([...questions, trimmedQuestion]);
    setNewQuestion("");
    message.success("问题添加成功");
  }, [newQuestion, questions, onChange, maxQuestions]);

  // 删除问题
  const removeQuestion = useCallback(
    (index: number) => {
      const newQuestions = questions.filter((_, i) => i !== index);
      onChange(newQuestions);
      message.success("问题已删除");
    },
    [questions, onChange],
  );

  // 清空问题列表
  const clearQuestions = useCallback(() => {
    onChange([]);
    message.success("问题列表已清空");
  }, [onChange]);

  // 加载问题集
  const loadQuestionSet = useCallback(
    (questionSet: QuestionSet) => {
      onChange(questionSet.questions);
      message.success(`已加载问题集: ${questionSet.name}`);
    },
    [onChange],
  );

  // 删除问题集
  const deleteQuestionSet = useCallback(
    (name: string) => {
      const updatedSets = savedQuestionSets.filter((set) => set.name !== name);
      setSavedQuestionSets(updatedSets);
      localStorage.setItem("questionSets", JSON.stringify(updatedSets));
      message.success("问题集删除成功");
    },
    [savedQuestionSets],
  );

  // 查看问题集JSON
  const viewQuestionSetJson = useCallback(
    (questionSet: QuestionSet) => {
      showJson(questionSet);
    },
    [showJson],
  );

  // 通用导出JSON函数
  const exportToJson = useCallback(
    (data: unknown, filename: string, successMessage: string) => {
      try {
        // 生成文件名
        const timestamp = new Date()
          .toISOString()
          .slice(0, 19)
          .replace(/:/g, "-");
        const finalFilename = `${filename}_${timestamp}.json`;

        // 创建并下载文件
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = finalFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        message.success(successMessage);
      } catch (error) {
        console.error("导出失败:", error);
        message.error("导出失败，请重试");
      }
    },
    [],
  );

  // 导出当前问题列表为JSON
  const exportCurrentQuestions = useCallback(() => {
    if (questions.length === 0) {
      message.warning("当前没有问题可导出");
      return;
    }

    const exportData = {
      questions: questions,
      export_metadata: {
        export_time: new Date().toISOString(),
        total_questions: questions.length,
      },
    };

    exportToJson(exportData, "current_questions", "当前问题已导出");
  }, [questions, exportToJson]);

  // 导出问题集为JSON
  const exportQuestionSet = useCallback(
    (questionSet: QuestionSet) => {
      exportToJson(
        questionSet,
        `question_set_${questionSet.name}`,
        "问题集已导出",
      );
    },
    [exportToJson],
  );

  // 文件上传处理
  const handleFileUpload = useCallback(
    async (file: UploadFile) => {
      try {
        setUploading(true);
        const rawFile = file.originFileObj;
        if (!rawFile) {
          message.error("无法读取上传文件");
          return false;
        }

        const uploadResult: QuestionFileUpload =
          await api.questions.parseFile(rawFile);

        // 合并问题，避免重复
        const existingQuestions = new Set(questions);
        const newQuestions = uploadResult.questions.filter(
          (q) => !existingQuestions.has(q),
        );

        onChange([...questions, ...newQuestions]);

        message.success(
          `文件解析成功！导入了 ${newQuestions.length} 个新问题${
            uploadResult.duplicates_removed > 0
              ? `，去除重复 ${uploadResult.duplicates_removed} 个`
              : ""
          }`,
        );

        // 显示警告信息
        if (uploadResult.warnings.length > 0) {
          Modal.warning({
            title: "导入警告",
            content: (
              <div>
                <p>文件导入成功，但有以下警告：</p>
                <ul>
                  {uploadResult.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            ),
          });
        }
      } catch (error) {
        console.error("文件上传失败:", error);
        message.error(`文件解析失败: ${error}`);
      } finally {
        setUploading(false);
      }

      return false; // 阻止自动上传
    },
    [questions, onChange],
  );

  return (
    <Card title="问题管理" className="question-manager">
      {/* 文件导入和模板选择 */}
      <div style={{ marginBottom: 16 }}>
        <Space wrap>
          <Upload
            beforeUpload={handleFileUpload}
            accept=".json"
            showUploadList={false}
            disabled={uploading}
          >
            <Button icon={<UploadOutlined />} loading={uploading}>
              导入JSON文件
            </Button>
          </Upload>

          <Button
            icon={<DownloadOutlined />}
            onClick={() => exportCurrentQuestions()}
            disabled={questions.length === 0}
          >
            导出JSON文件
          </Button>

          {savedQuestionSets.length > 0 && (
            <Select
              placeholder="选择问题集模板"
              style={{ width: 200 }}
              onChange={(value) => {
                const selectedSet = savedQuestionSets.find(
                  (set) => set.name === value,
                );
                if (selectedSet) {
                  loadQuestionSet(selectedSet);
                }
              }}
            >
              {savedQuestionSets.map((set) => (
                <Option key={set.name} value={set.name}>
                  <Space>
                    <FileTextOutlined />
                    {set.name} ({set.questions.length}题)
                  </Space>
                </Option>
              ))}
            </Select>
          )}
        </Space>
      </div>

      {/* 手动添加问题 */}
      <div style={{ marginBottom: 16 }}>
        <Input.Group compact>
          <Input
            style={{ width: "calc(100% - 80px)" }}
            value={newQuestion}
            onChange={(e) => setNewQuestion(e.target.value)}
            placeholder="手动添加问题"
            onPressEnter={addQuestion}
            maxLength={500}
            disabled={questions.length >= maxQuestions}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={addQuestion}
            disabled={questions.length >= maxQuestions}
          >
            添加
          </Button>
        </Input.Group>

        {questions.length >= maxQuestions && (
          <Alert
            message={`已达到最大问题数量限制 (${maxQuestions})`}
            type="warning"
            style={{ marginTop: 8 }}
            showIcon
          />
        )}
      </div>

      {/* 问题列表 */}
      {questions.length > 0 && (
        <div>
          {/* 操作栏 */}
          <div
            style={{
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <Tag color="blue">已添加问题 ({questions.length})</Tag>

            <Popconfirm
              title="确定要清空所有问题吗？"
              onConfirm={clearQuestions}
              okText="确定"
              cancelText="取消"
            >
              <Button danger size="small" icon={<ClearOutlined />}>
                清空列表
              </Button>
            </Popconfirm>
          </div>

          {/* 问题列表 */}
          <div
            style={{
              maxHeight: "400px",
              overflowY: "auto",
              border: "1px solid #d9d9d9",
              borderRadius: "6px",
              padding: "8px",
            }}
          >
            <List
              size="small"
              dataSource={questions}
              renderItem={(question, index) => (
                <List.Item
                  className="question-item"
                  actions={[
                    <Tooltip key="delete" title="删除问题">
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => removeQuestion(index)}
                      />
                    </Tooltip>,
                  ]}
                  style={{
                    padding: "8px 12px",
                    borderRadius: "4px",
                    marginBottom: "4px",
                    border: "1px solid #f0f0f0",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <span
                      style={{
                        color: "#666",
                        marginRight: 8,
                        fontSize: "12px",
                        fontWeight: "bold",
                      }}
                    >
                      {index + 1}.
                    </span>
                    <span style={{ wordBreak: "break-word" }}>{question}</span>
                  </div>
                </List.Item>
              )}
            />
          </div>
        </div>
      )}

      {/* 保存的问题集管理 */}
      {savedQuestionSets.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h4>已保存的问题集</h4>
          <List
            size="small"
            dataSource={savedQuestionSets}
            renderItem={(set) => (
              <List.Item
                actions={[
                  <Button
                    key="load"
                    type="link"
                    size="small"
                    onClick={() => loadQuestionSet(set)}
                  >
                    加载
                  </Button>,
                  <Button
                    key="view"
                    type="link"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => viewQuestionSetJson(set)}
                  >
                    查看JSON
                  </Button>,
                  <Button
                    key="export"
                    type="link"
                    size="small"
                    onClick={() => exportQuestionSet(set)}
                  >
                    导出JSON
                  </Button>,
                  <Popconfirm
                    key="delete-confirm"
                    title={`确定删除问题集 "${set.name}" 吗？`}
                    onConfirm={() => deleteQuestionSet(set.name)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button key="delete" type="link" danger size="small">
                      删除
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={<FileTextOutlined />}
                  title={set.name}
                  description={`${set.questions.length} 个问题`}
                />
              </List.Item>
            )}
          />
        </div>
      )}

      {/* JSON显示模态框 */}
      <JsonDisplayModal
        open={jsonModalVisible}
        onClose={hideJson}
        title="问题集JSON数据"
        jsonData={jsonData}
        width={800}
      />
    </Card>
  );
};
