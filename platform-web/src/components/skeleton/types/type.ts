import { baseSkeletonProps } from '../props'
import type { ExtractPropTypes, PropType } from 'vue';

export type BaseSkeletonProps =  Partial<ExtractPropTypes<ReturnType<typeof baseSkeletonProps>>>
