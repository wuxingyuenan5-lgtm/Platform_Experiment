// 能变色的单元格数据 0-0.01% 白色；>0.01% 红色；<0 绿色
import { computed, defineComponent, watch, ref } from 'vue';
import { basicStringAnProps } from '../../props';

export default defineComponent({
  props: basicStringAnProps,
  setup(props) {
    const curClass = ref('');
    const style = computed(() => {
      const _style = {
        height: 'inherit',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      };
      const _val = props.value ? parseFloat(props.value) : 0;
      if (_val > 0.01) {
        _style.color = '#ff5260';
      } else if (_val < 0) {
        _style.color = '#00ae93';
      }
      return _style;
    });
    watch(
      () => props.value,
      (cur, old) => {
        const _cur = parseFloat(cur || 0),
          _old = parseFloat(old || 0);
        const _curClass = curClass.value;
        // console.log(_cur, _old, _curClass);

        if (_cur > 0.01) {
          curClass.value = _cur > _old ? 'shortstylefr2' : 'longstylefr2';
        } else if (_cur < 0) {
          curClass.value = _cur > _old ? 'shortstylefr' : 'longstylefr';
        }
        if (Math.abs(_cur) >= 0.05) {
          curClass.value += ' font-medium';
        }
        if (_curClass == curClass.value) {
          curClass.value = '';
          setTimeout(() => {
            curClass.value = _curClass;
          });
        }
      },
      { immediate: true },
    );
    // console.log('props.value===', props.value);

    return () => (
      <div class={curClass.value} style={style.value}>
        {props.value || 0}
      </div>
    );
  },
});
