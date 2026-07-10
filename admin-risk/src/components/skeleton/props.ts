import { emptyProps } from "ant-design-vue/es/empty"
import { skeletonProps } from "ant-design-vue/es/skeleton"
import type { VNode } from "vue"
import { Empty } from "ant-design-vue"
export function baseSkeletonProps() {
    return {
        ...skeletonProps(),
        active: {
            type: Boolean,
            default: true
        },
        showEmpty: {
            type: Boolean,
            default: false
        },
        emptyProps: {
            ...emptyProps(),
            // image: {
            //     type: Object as PropType<VNode>,
            //     default: Empty.PRESENTED_IMAGE_SIMPLE
            // }
        }
    }
}