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
  };
  export default defineComponent({
    name: 'SimpleContainer',
    props: collapseContainerProps,
    setup(props, { slots }) {
      return () => {
        return props.loading ? (
          <Skeleton active={props.loading} paragraph={props.paragraph} />
        ) : (
          <div>
            <div class="h-6 flex justify-between items-center pb-2">
              <div class="text-base font-500">{slots?.title?.() || props.title}</div>
              <div>{slots.action?.()}</div>
            </div>
            {slots.default?.()}
          </div>
        );
      };
    },
  });
</script>
