/**
 * 通用表单管理Hook
 * 提供表单状态管理、验证、提交等功能
 */

import React, { useState, useCallback, useMemo } from "react";
import type { ValidationError } from "../types";

interface UseFormOptions<T> {
  initialValues?: Partial<T>;
  validate?: (values: T) => ValidationError[];
  onSubmit?: (values: T) => Promise<void> | void;
}

interface UseFormReturn<T> {
  // 状态
  values: T;
  errors: ValidationError[];
  touched: Record<keyof T, boolean>;
  isSubmitting: boolean;
  isValid: boolean;

  // 操作
  setValue: <K extends keyof T>(field: K, value: T[K]) => void;
  setValues: (values: Partial<T>) => void;
  setError: (field: keyof T, message: string) => void;
  clearError: (field: keyof T) => void;
  clearAllErrors: () => void;
  setTouched: (field: keyof T, touched?: boolean) => void;
  handleSubmit: (e?: React.FormEvent) => Promise<void>;
  reset: (newValues?: Partial<T>) => void;

  // 辅助方法
  getFieldError: (field: keyof T) => string | undefined;
  hasFieldError: (field: keyof T) => boolean;
  isFieldTouched: (field: keyof T) => boolean;
}

export function useForm<T extends object>(
  options: UseFormOptions<T> = {},
): UseFormReturn<T> {
  const { initialValues = {} as T, validate, onSubmit } = options;

  // 状态管理
  const [values, setFormValues] = useState<T>({ ...initialValues } as T);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [touched, setTouchedFields] = useState<Record<keyof T, boolean>>(
    {} as Record<keyof T, boolean>,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 计算属性
  const isValid = useMemo(() => errors.length === 0, [errors]);

  // 设置单个字段值
  const setValue = useCallback(<K extends keyof T>(field: K, value: T[K]) => {
    setFormValues((prev) => ({
      ...prev,
      [field]: value,
    }));

    // 标记字段为已触摸
    setTouchedFields((prev) => ({
      ...prev,
      [field]: true,
    }));

    // 清除该字段的错误
    setErrors((prev) => prev.filter((error) => error.field !== field));
  }, []);

  // 设置多个字段值
  const setValues = useCallback((newValues: Partial<T>) => {
    setFormValues((prev) => ({
      ...prev,
      ...newValues,
    }));

    // 标记字段为已触摸
    const touchedFields = Object.keys(newValues).reduce(
      (acc, key) => ({
        ...acc,
        [key]: true,
      }),
      {},
    );

    setTouchedFields((prev) => ({
      ...prev,
      ...touchedFields,
    }));
  }, []);

  // 设置字段错误
  const setError = useCallback((field: keyof T, message: string) => {
    setErrors((prev) => {
      // 移除该字段的现有错误
      const filtered = prev.filter((error) => error.field !== field);
      // 添加新错误
      return [...filtered, { field: field as string, message }];
    });
  }, []);

  // 清除字段错误
  const clearError = useCallback((field: keyof T) => {
    setErrors((prev) => prev.filter((error) => error.field !== field));
  }, []);

  // 清除所有错误
  const clearAllErrors = useCallback(() => {
    setErrors([]);
  }, []);

  // 设置字段触摸状态
  const setTouched = useCallback(
    (field: keyof T, isTouched: boolean = true) => {
      setTouchedFields((prev) => ({
        ...prev,
        [field]: isTouched,
      }));
    },
    [],
  );

  // 表单提交
  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      if (e) {
        e.preventDefault();
      }

      try {
        setIsSubmitting(true);
        clearAllErrors();

        // 标记所有字段为已触摸
        const allTouched = Object.keys(values).reduce(
          (acc, key) => ({
            ...acc,
            [key]: true,
          }),
          {},
        );
        setTouchedFields(allTouched as Record<keyof T, boolean>);

        // 验证表单
        if (validate) {
          const validationErrors = validate(values);
          if (validationErrors.length > 0) {
            setErrors(validationErrors);
            return;
          }
        }

        // 提交表单
        if (onSubmit) {
          await onSubmit(values);
        }
      } catch (error) {
        console.error("表单提交失败:", error);

        // 如果是验证错误，设置到errors中
        if (error && typeof error === "object" && "field" in error) {
          const err = error as { field: unknown; message?: string };
          if (typeof err.field === "string") {
            setError(err.field as keyof T, err.message || "未知错误");
          }
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [values, validate, onSubmit, clearAllErrors, setError],
  );

  // 重置表单
  const reset = useCallback(
    (newValues?: Partial<T>) => {
      const resetValues = newValues
        ? { ...initialValues, ...newValues }
        : initialValues;
      setFormValues({ ...resetValues } as T);
      setErrors([]);
      setTouchedFields({} as Record<keyof T, boolean>);
      setIsSubmitting(false);
    },
    [initialValues],
  );

  // 辅助方法
  const getFieldError = useCallback(
    (field: keyof T): string | undefined => {
      const error = errors.find((err) => err.field === field);
      return error?.message;
    },
    [errors],
  );

  const hasFieldError = useCallback(
    (field: keyof T): boolean => {
      return errors.some((err) => err.field === field);
    },
    [errors],
  );

  const isFieldTouched = useCallback(
    (field: keyof T): boolean => {
      return Boolean(touched[field]);
    },
    [touched],
  );

  return {
    // 状态
    values,
    errors,
    touched,
    isSubmitting,
    isValid,

    // 操作
    setValue,
    setValues,
    setError,
    clearError,
    clearAllErrors,
    setTouched,
    handleSubmit,
    reset,

    // 辅助方法
    getFieldError,
    hasFieldError,
    isFieldTouched,
  };
}
