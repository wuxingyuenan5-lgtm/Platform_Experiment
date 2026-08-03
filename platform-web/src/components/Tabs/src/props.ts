import type { SizeType, BasicTabsOption } from './types/tabs';

export const basicProps = {
  options: {
    type: Array as PropType<BasicTabsOption[]>,
    default: () => [],
  },
  value: [String, Number],
  size: {
    type: String as PropType<SizeType>,
    default: 'default',
  },
  noBorder: {
    type: Boolean,
    default: false,
  },
};
