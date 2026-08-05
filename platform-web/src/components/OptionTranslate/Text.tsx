import { computed, defineComponent } from 'vue';
import { basicProps } from './props';

export default defineComponent({
  props: basicProps,
  setup(props) {
    const optionsMap = computed<Record<string, LabelValueOptions[number]>>(() => {
      return (props.options || []).reduce<Record<string, LabelValueOptions[number]>>((acc, cur) => {
        acc[String(cur.value)] = cur;
        return acc;
      }, {});
    });

    function renderItem(color = '') {
      let style: Record<string, string> | undefined;
      let prefixElm;
      let classBasic = 'break-all truncate';
      if (props.type === 'text') {
        style = { color };
      } else if (props.type === 'dot') {
        classBasic += ' flex items-center';
        style = {
          position: 'relative',
          paddingLeft: '14px',
        };
        prefixElm = (
          <span
            style={{
              display: 'inline-block',
              position: 'absolute',
              left: 0,
              top: '50%',
              marginTop: '-5px',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: color,
            }}
          ></span>
        );
      }
      return { style, prefixElm, classBasic };
    }
    return () => {
      const item = optionsMap.value[String(props.value)];
      const label = String(item?.label ?? props.value ?? '');
      const color = String(item?.color ?? '');
      const { style, prefixElm, classBasic } = renderItem(color);
      return (
        <div class={classBasic} title={label} style={style}>
          {prefixElm}
          {label}
        </div>
      );
    };
  },
});
