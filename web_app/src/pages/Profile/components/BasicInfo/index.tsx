/**
 * 基础信息组件
 *
 * 用途：展示用户基础信息（邮箱、手机、性别、年龄段、简介）
 * 使用示例：
 * ```tsx
 * <BasicInfo userProfile={userProfile} />
 * ```
 *
 * Props 说明：
 * - userProfile: IUserProfile - 用户信息对象
 */

import { Calendar, FileText, Mail, Phone, User } from 'lucide-react';
import React from 'react';
import { Icon } from '@/components';
import type { IUserProfile } from '@/types';
import './index.less';

interface IBasicInfoProps {
  /** 用户信息 */
  userProfile: IUserProfile;
}

/**
 * 基础信息组件
 */
const BasicInfo: React.FC<IBasicInfoProps> = ({ userProfile }) => {
  /**
   * 格式化性别显示
   */
  const getGenderText = (gender?: string | null): string => {
    if (!gender) return 'Not set';
    const genderMap: Record<string, string> = {
      MALE: 'Male',
      FEMALE: 'Female',
      OTHER: 'Other',
    };
    return genderMap[gender] || 'Not set';
  };

  /**
   * 信息项组件
   */
  const InfoItem: React.FC<{
    icon: typeof Mail;
    label: string;
    value?: string | null;
    placeholder?: string;
  }> = ({ icon, label, value, placeholder = 'Not set' }) => (
    <div className="info-item">
      <div className="info-label">
        <Icon icon={icon} size={18} color="#6366f1" />
        <span>{label}</span>
      </div>
      <div className="info-value">{value || placeholder}</div>
    </div>
  );

  return (
    <div className="basic-info-card">
      <h2 className="card-title">Basic Information</h2>

      <div className="info-list">
        <InfoItem icon={Mail} label="Email" value={userProfile.email} placeholder="No email set" />

        <InfoItem icon={Phone} label="Phone" value={userProfile.phone} placeholder="No phone set" />

        <InfoItem icon={User} label="Gender" value={getGenderText(userProfile.gender)} />

        <InfoItem icon={Calendar} label="Age Group" value={userProfile.age_group} />

        <InfoItem
          icon={FileText}
          label="Bio"
          value={userProfile.description}
          placeholder="No bio"
        />
      </div>
    </div>
  );
};

export default BasicInfo;
