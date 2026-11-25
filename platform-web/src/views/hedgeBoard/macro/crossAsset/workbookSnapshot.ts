export interface WorkbookAsset {
  group: string;
  category: string;
  code: string;
  name: string;
  proxy: string | null;
  activity: string | null;
  activityRank: number | null;
  attentionAge: number | null;
  day: string | null;
  dayAge: number | null;
  week: string | null;
  weekAge: number | null;
  month: string | null;
  monthAge: number | null;
  position: number | null;
  relativeStrength: number | null;
  relativeMomentum: number | null;
  relativeTurn: number | null;
  relativeAge: number | null;
  relativeState: string | null;
  relativeReturn: number | null;
  previousRelativeState: string | null;
  previousRelativeReturn: number | null;
  previousRelativeAge: number | null;
  flowAge: number | null;
  flowState: string | null;
  flowReturn: number | null;
  previousFlowState: string | null;
  previousFlowReturn: number | null;
  flowValue: number | null;
  flowChange: number | null;
  momentumAge: number | null;
  momentumState: string | null;
  momentumReturn: number | null;
  previousMomentumState: string | null;
  previousMomentumReturn: number | null;
  momentumValue: number | null;
  momentumChange: number | null;
}

export interface WorkbookSnapshot {
  version: 1;
  date: string;
  pools: Record<'core' | 'tools', { file: string; sheet: string; rows: WorkbookAsset[] }>;
}
