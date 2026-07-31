<script lang="tsx">
  import { defineComponent } from 'vue';
  import { SkeletonParagraphProps } from 'ant-design-vue/es/skeleton/Paragraph';
  import { Skeleton } from 'ant-design-vue';

  const collapseContainerProps = {
    title: {
      type: String,
      required: true,
    },
    loading: { type: Boolean },
    paragraph: {
      type: Object as PropType<SkeletonParagraphProps>,
      default: () => ({}),
    },
    bgType: {
      type: String,
      default: 'default',
      validator(value) {
        return ['default', 'gary'].includes(value);
      },
    },
  };
  export default defineComponent({
    name: 'PanelContainer',
    props: collapseContainerProps,
    setup(props, { slots }) {
      return () => {
        return props.loading ? (
          <Skeleton active={props.loading} paragraph={props.paragraph} />
        ) : (
          <div class={['panel', props.bgType]}>
            <div class="panel-title flex justify-between items-center mx-4 py-2">
              <div>{props.title}</div>
              <div>{slots.action?.()}</div>
            </div>
            {slots.default?.()}
          </div>
        );
      };
    },
  });
</script>
<style lang="less" scoped>
  .panel {
    background-color: @component-background;

    &.gary {
      background-color: @control-bg;
    }
  }

  .panel-title {
    height: 38px;
    border-bottom: 1px solid @border-color-base;
    line-height: 22px;
  }
</style>
