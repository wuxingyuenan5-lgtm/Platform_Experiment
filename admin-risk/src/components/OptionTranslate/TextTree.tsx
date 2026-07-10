import { computed, defineComponent } from 'vue';
import { basicTreeProps } from './props';

export default defineComponent({
  props: basicTreeProps,
  setup(props) {
    const curVal = computed(() => {
      let _val: any = props.value;
      if (props.value) {
        let item: any = props.options;
        _val = props.value.reduce((pre, cur) => {
          item = findItem(cur, item);
          const _label = pre + '/' + item?.label;
          item = item?.children;
          return _label;
        }, '');
        _val = _val?.substr(1);
      }
      return _val;
    });
    function findItem(key: any, arr: LabelValueOptions | undefined) {
      if (!key || !arr) return '';
      return arr.find((item) => item.value === key);
    }
    return () => {
      return <div class="truncate">{curVal.value}</div>;
    };
  },
});
