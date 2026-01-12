import { useAuthStore } from '@/store/authStore';

export type UserTier = 'BASIC' | 'PREMIUM';

export interface TierFeatures {
  canViewDistrictAggregates: boolean;
  canViewStationLocations: boolean;
  canDrilldownDistricts: boolean;
  canSwitchPollutantLayers: boolean;
  canUseGeolocation: boolean;
  canGenerateCustomReports: boolean;
  canViewTrendAnalysis: boolean;
  maxReportDays: number;
}

const TIER_FEATURES: Record<UserTier, TierFeatures> = {
  BASIC: {
    canViewDistrictAggregates: true,
    canViewStationLocations: true,
    canDrilldownDistricts: false,
    canSwitchPollutantLayers: false,
    canUseGeolocation: false,
    canGenerateCustomReports: false,
    canViewTrendAnalysis: false,
    maxReportDays: 0,
  },
  PREMIUM: {
    canViewDistrictAggregates: true,
    canViewStationLocations: true,
    canDrilldownDistricts: true,
    canSwitchPollutantLayers: true,
    canUseGeolocation: true,
    canGenerateCustomReports: true,
    canViewTrendAnalysis: true,
    maxReportDays: 30,
  },
};

export function useUserTier() {
  const { user } = useAuthStore();

  const tier: UserTier = (user?.subscription_tier as UserTier) || 'BASIC';
  const features = TIER_FEATURES[tier];
  const isPremium = tier === 'PREMIUM';
  const isBasic = tier === 'BASIC';

  return {
    tier,
    features,
    isPremium,
    isBasic,
  };
}
