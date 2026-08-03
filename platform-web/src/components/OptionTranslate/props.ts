import { TextTranslateType } from './types';

export const basicProps = {
  value: {
    type: [String, Number, Boolean],
    default: '',
    required: true, // 必传
  },
  options: {
    type: Array as PropType<LabelValueOptions>,
  },
  type: {
    type: String as PropType<TextTranslateType>,
    default: 'text',
  },
};

export const basicTreeProps = {
  value: {
    type: Array,
    default: () => [],
  },
  options: {
    type: Array as PropType<LabelValueOptions>,
    require: true,
  },
};
