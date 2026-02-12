import type {
  FestivalMemoryConfigItem,
  FestivalMemoryRunStatus,
} from "../types";

export const resolveFestivalMemoryRunStatus = (
  config: FestivalMemoryConfigItem,
): FestivalMemoryRunStatus => {
  if (config.run_status) {
    return config.run_status;
  }
  return config.last_run_at ? "completed" : "idle";
};

export const getFestivalMemoryRunStatusMeta = (
  status: FestivalMemoryRunStatus,
): { label: string; color: string } => {
  switch (status) {
    case "running":
      return { label: "运行中", color: "processing" };
    case "completed":
      return { label: "已完成", color: "success" };
    case "failed":
      return { label: "失败", color: "error" };
    case "idle":
    default:
      return { label: "未运行", color: "default" };
  }
};

export const canShowFestivalMemoryResults = (
  config: FestivalMemoryConfigItem,
): boolean => {
  const status = resolveFestivalMemoryRunStatus(config);
  if (status === "running") {
    return false;
  }
  return Boolean(config.run_finished_at || config.last_run_at);
};
