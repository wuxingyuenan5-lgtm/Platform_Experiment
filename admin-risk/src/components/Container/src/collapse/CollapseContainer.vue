<script lang="tsx">
  import { ref, unref, defineComponent, type PropType, type ExtractPropTypes } from 'vue';
  import { isNil } from 'lodash-es';
  import { Skeleton } from 'ant-design-vue';
  import { useTimeoutFn } from '@vben/hooks';
  import { CollapseTransition } from '@/components/Transition';
  import CollapseHeader from './CollapseHeader.vue';
  import { triggerWindowResize } from '@/utils/event';
  import { useDesign } from '@/hooks/web/useDesign';
  import { SkeletonParagraphProps } from 'ant-design-vue/es/skeleton/Paragraph';

  export enum CollapseContainerType {
    normal = 1,
    light,
    light2,
    darkHeader,
  }
  export enum CollapseContainerSize {
    middle = '',
    small = 'is-small',
  }
  const collapseContainerProps = {
    size: { type: String as PropType<CollapseContainerSize>, default: '' },
    title: { type: String, default: '' },
    noTitle: { type: Boolean },
    type: { type: Number as PropType<CollapseContainerType> },
    loading: { type: Boolean },
    bodyPadding: { type: String, default: 'px-4' },
    /**
     *  Can it be expanded
     */
    canExpan: { type: Boolean, default: true },
    /**
     * Warm reminder on the right side of the title
     */
    helpMessage: {
      type: [Array, String] as PropType<string[] | string>,
      default: '',
    },
    /**
     * Whether to trigger window.resize when expanding and contracting,
     * Can adapt to tables and forms, when the form shrinks, the form triggers resize to adapt to the height
     */
    triggerWindowResize: { type: Boolean },
    /**
     * Delayed loading time
     */
    lazyTime: { type: Number, default: 0 },

    paragraph: {
      type: Object as PropType<SkeletonParagraphProps>,
      default: () => ({}),
    },
  };

  export type CollapseContainerProps = ExtractPropTypes<typeof collapseContainerProps>;

  export default defineComponent({
    name: 'CollapseContainer',

    props: collapseContainerProps,

    setup(props, { expose, slots }) {
      const { prefixCls } = useDesign('collapse-container');

      const show = ref(true);

      const handleExpand = (val: boolean) => {
        show.value = isNil(val) ? !show.value : val;
        if (props.triggerWindowResize) {
          // 200 milliseconds here is because the expansion has animation,
          useTimeoutFn(triggerWindowResize, 200);
        }
      };

      expose({ handleExpand });
      function renderBody() {
        return props.loading ? (
          <Skeleton active={props.loading} paragraph={props.paragraph} />
        ) : (
          <div class={`${prefixCls}__body`} v-show={show.value}>
            {slots.default?.()}
          </div>
        );
      }
      return () => (
        <div
          class={[
            unref(prefixCls),
            props?.type == CollapseContainerType.light && 'is-light',
            props?.type == CollapseContainerType.light2 && 'is-light2',
            props?.size,
          ]}
        >
          {!props.noTitle && (
            <CollapseHeader
              {...props}
              prefixCls={unref(prefixCls)}
              onExpand={handleExpand}
              show={show.value}
              class={[
                props?.type == CollapseContainerType.darkHeader && 'is-darkHeader',
                props?.type == CollapseContainerType.light2 && 'is-light2',
              ]}
              v-slots={{
                title: slots.title,
                action: slots.action,
              }}
            />
          )}
          <div class={props.bodyPadding}>
            {props.canExpan ? (
              <CollapseTransition enable={true}>{renderBody()}</CollapseTransition>
            ) : (
              renderBody()
            )}
          </div>
          {slots.footer && <div class={`${prefixCls}__footer`}>{slots.footer()}</div>}
        </div>
      );
    },
  });
</script>

<style lang="less">
  @prefix-cls: ~'@{namespace}-collapse-container';

  .@{prefix-cls} {
    transition: all 0.3s ease-in-out;
    border-radius: 0;
    // background-color: @component-background;

    &.is-light {
      background-color: @component-background;
      .@{namespace}-basic-title {
        // color: @white;
      }
    }

    &.is-light2 {
      background-color: fade(#acacacff, 10%);
      .@{namespace}-basic-title {
        color: #d1d4dc;
        font-weight: 400;
      }
    }

    &.is-small {
      border-radius: 4px;

      .vg-collapse-container__header {
        height: 32px;
      }
    }

    &__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 44px;
      border-top-left-radius: 0;
      border-top-right-radius: 0;
      // border-bottom: 1px solid @border-color-light;
      &.is-darkHeader {
        background-color: @component-header-bg;
      }

      &.is-light2 {
        background-color: rgb(45 47 58 / 40%);
      }
    }

    &__footer {
      border-top: 1px solid @border-color-light;
    }

    &__action {
      display: flex;
      flex: 1;
      align-items: center;
      justify-content: flex-end;
      text-align: right;
    }
  }
</style>
