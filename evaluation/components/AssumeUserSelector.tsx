/**
 * Allow evaluator (superuser) to assume an arbitrary user identity so that
 * chat and voice chat load that user's conversation history with the character.
 */

import React, { useState, useEffect, useCallback } from "react";
import { Select, Typography } from "antd";
import { UserSwitchOutlined } from "@ant-design/icons";
import api, { getAssumeUserId, setAssumeUserId } from "../services/api";
import { userDisplayId } from "../utils/userDisplayId";

const STORAGE_KEY = "evaluation_assume_user_id";

export const AssumeUserSelector: React.FC = () => {
  const [isSuperuser, setIsSuperuser] = useState<boolean | null>(null);
  const [users, setUsers] = useState<Array<{ id: string; label: string }>>([]);
  const [searching, setSearching] = useState(false);
  const [value, setValue] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(STORAGE_KEY) || null;
  });

  useEffect(() => {
    const stored = value || localStorage.getItem(STORAGE_KEY);
    if (stored) setAssumeUserId(stored);
    else setAssumeUserId(null);
  }, [value]);

  const fetchProfile = useCallback(async () => {
    try {
      const profile = (await api.users.me()) as {
        is_superuser?: boolean;
      } | null;
      setIsSuperuser(Boolean(profile?.is_superuser));
    } catch {
      setIsSuperuser(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const searchUsers = useCallback(async (search?: string) => {
    setSearching(true);
    try {
      const result = await api.users.searchUsers({
        search: search || undefined,
        limit: 50,
        skip: 0,
      });
      const list = (result?.users ?? []).map(
        (u: { id: string; nickname?: string; readable_id?: string | null }) => ({
          id: u.id,
          label:
            [u.nickname, userDisplayId(u)].filter(Boolean).join(" · ") || u.id,
        }),
      );
      setUsers(list);
    } catch {
      setUsers([]);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    if (isSuperuser) searchUsers();
  }, [isSuperuser, searchUsers]);

  const handleChange = (v: string | null) => {
    const next = v && v.trim() ? v.trim() : null;
    setValue(next);
    setAssumeUserId(next);
    if (typeof window !== "undefined") {
      if (next) localStorage.setItem(STORAGE_KEY, next);
      else localStorage.removeItem(STORAGE_KEY);
    }
  };

  if (isSuperuser === null || !isSuperuser) return null;

  const options = [
    { value: "", label: "Me (no assume)" },
    ...users.map((u) => ({ value: u.id, label: u.label })),
  ];

  return (
    <div
      style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 200 }}
    >
      <UserSwitchOutlined style={{ color: "#666" }} />
      <Typography.Text
        type="secondary"
        style={{ whiteSpace: "nowrap", fontSize: 12 }}
      >
        Assume user:
      </Typography.Text>
      <Select
        placeholder="Me"
        allowClear
        showSearch
        optionFilterProp="label"
        options={options}
        value={value || undefined}
        onChange={(v) => handleChange(v ?? null)}
        onSearch={(q) => searchUsers(q)}
        loading={searching}
        style={{ flex: 1, minWidth: 160 }}
        size="small"
      />
    </div>
  );
};
