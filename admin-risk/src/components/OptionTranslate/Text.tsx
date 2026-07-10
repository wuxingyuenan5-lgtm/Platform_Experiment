import { computed, defineComponent } from 'vue';
import { basicProps } from './props';

export default defineComponent({
  props: basicProps,
  setup(props) {
    const { value, options, type } = props;
    const optionsMap = computed(() => {
      return options?.reduce((acc, cur) => {
        acc[cur.value] = cur;
        return acc;
      }, {});
    });

    function renderItem(color: string) {
      let style: any,
        prefixElm: any,
        classBasic: string = 'break-all truncate';
      if (type === 'text') {
        style = { color };
      } else if (type === 'dot') {
        classBasic += 'flex items-center';
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
      const item = optionsMap.value?.[value];
      const { style, prefixElm, classBasic } = renderItem(item?.color);
      return (
        <div class={classBasic} title={item?.label} style={style}>
          {prefixElm}
          {item?.label || value}
        </div>
      );
    };
  },
});
