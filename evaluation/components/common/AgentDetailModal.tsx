import React from "react";
import { Button, Modal, Spin } from "antd";
import type { Agent } from "../../types";
import AgentInfoDisplay from "./AgentInfoDisplay";

type AgentDetailModalActionKey = "close" | "edit";

interface AgentDetailModalProps {
  open: boolean;
  agent: Agent | null;
  /** When true, show loading spinner until agent is set */
  loading?: boolean;
  onClose: () => void;
  onEdit?: (agent: Agent) => void;
  onDeleteBackgroundImage?: (imageUrl: string) => void;
  title?: React.ReactNode;
  width?: number;
}

// 关键步骤总结：把 AgentManagePage 中“角色详情弹窗壳”抽离为通用组件，
// 以便 ChatPage 与 AgentManagePage 共享同一套展示与按钮逻辑。
export const getAgentDetailModalActionKeys = (
  agent: Agent | null,
  hasEditHandler: boolean,
): AgentDetailModalActionKey[] => {
  if (!agent || !hasEditHandler) {
    return ["close"];
  }
  return ["close", "edit"];
};

export const AgentDetailModal: React.FC<AgentDetailModalProps> = ({
  open,
  agent,
  loading = false,
  onClose,
  onEdit,
  onDeleteBackgroundImage,
  title = "角色详情",
  width = 800,
}) => {
  const actionKeys = getAgentDetailModalActionKeys(agent, Boolean(onEdit));

  const footer = actionKeys.map((actionKey) => {
    if (actionKey === "edit") {
      return (
        <Button
          key="edit"
          type="primary"
          onClick={() => {
            if (agent && onEdit) {
              onEdit(agent);
            }
          }}
        >
          编辑
        </Button>
      );
    }

    return (
      <Button key="close" onClick={onClose}>
        关闭
      </Button>
    );
  });

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onClose}
      footer={footer}
      width={width}
    >
      {loading && !agent ? (
        <div style={{ padding: 48, textAlign: "center" }}>
          <Spin size="large" />
        </div>
      ) : (
        agent && (
          <AgentInfoDisplay
            agent={agent}
            onDeleteBackgroundImage={onDeleteBackgroundImage}
          />
        )
      )}
    </Modal>
  );
};

export default AgentDetailModal;
