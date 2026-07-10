<template>
  <Dropdown v-model:open="dropdownOpen" :trigger="['click']">
    <div ref="slotCont">
      <slot></slot>
    </div>
    <template #overlay>
      <div class="cascader-pop">
        <template v-if="showSearch">
          <div :style="menuStyle" class="p-2">
            <Input placeholder="请输入关键字" v-model:value="searchInfo.value">
              <template #prefix><SearchOutlined /></template
            ></Input>
          </div>
        </template>
        <template v-if="!searchInfo.value">
          <component :is="renderMemus" />
        </template>
        <template v-else>
          <div class="max-h-60 min-h-40 overflow-y-auto">
            <template v-if="filterOptions?.length > 0">
              <component :is="renderSearchMenus" />
              <!-- <div v-for="items in filterOptions" :key="items?.label">
                <div class="px-2" v-for="item in items?.children" :key="item?.value">
                  <div>{{ items?.label }} / {{ item?.label }}</div>
                  <div
                    v-for="itemChild in item?.children"
                    :key="itemChild?.value"
                    @click="handleClickSearch(items.label, item.label, itemChild)"
                    class="rounded cursor-pointer flex items-center justify-between py-1 px-2 hover:bg-[#64656c]"
                    >{{ itemChild?.label }}</div
                  >
                </div>
              </div> -->
            </template>
            <Empty v-else :image="Empty.PRESENTED_IMAGE_SIMPLE" class="!pt-10" />
          </div>
        </template>
      </div>
    </template>
  </Dropdown>
</template>
<script lang="tsx" setup>
  import { Dropdown, Empty, Input } from 'ant-design-vue';
  import { computed, ref, watch, onMounted, onUnmounted, nextTick, reactive } from 'vue';
  import Icon from '@/components/Icon/Icon.vue';
  import { SearchOutlined } from '@ant-design/icons-vue';
  import { watchDebounced } from '@vueuse/shared';

  const emits = defineEmits(['change']);
  const props = defineProps({
    width: {
      type: [String, Number],
      default: '200px',
    },
    options: {
      type: Array,
      default: () => [],
    },
    showSearch: {
      type: Boolean,
      default: false,
    },
  });

  const slotCont = ref();
  const menuStyle = ref();
  const curValue = ref([]);
  const curOptions = ref([]);
  const dropdownOpen = ref(false);
  const filterOptions = ref([]); // 过滤后的数据
  const searchInfo = reactive({
    value: '',
  });
  watch(
    () => props?.options,
    (curV) => {
      curOptions.value = JSON.parse(JSON.stringify(curV));
      nextTick(() => {
        menuStyleFn();
      });
    },
    { immediate: true },
  );
  watch(
    () => dropdownOpen.value,
    (curV) => {
      if (!curV) {
        removeSelected(curOptions.value);
      }
    },
  );
  // 过滤函数，根据条件过滤数组
  function filterArray(arr, condition) {
    const _arr: any = [];
    arr?.forEach((item) => {
      if (!item?.disabled) {
        if (item?.children?.length > 0) {
          if (filterArray(item.children, condition)?.length > 0) {
            return _arr.push({
              ...item,
              children: filterArray(item.children, condition),
            });
          }
        } else {
          if (!condition(item)) return;
          _arr.push(item);
        }
      }
    });
    return _arr;
  }
  const condition = (item) => item?.label?.toLowerCase().includes(searchInfo.value.toLowerCase());

  watchDebounced(
    () => searchInfo.value,
    (curV) => {
      filterOptions.value = filterArray(curOptions.value, condition);
    },
    { debounce: 200 },
  );
  function renderMemus() {
    return (
      <div class="cascader-menus">
        {curOptions.value?.length > 0 ? (
          renderMemu(curOptions.value)
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} class="!pt-10 mx-auto" />
        )}
      </div>
    );
  }
  function renderMemu(arr?: any[]) {
    function _menuElm(options) {
      return (
        <div class="cascader-menu" style={menuStyle.value}>
          {options?.map((item) => {
            return (
              <div
                class={[
                  'cascader-menu-item',
                  item?.selected && 'active',
                  item?.disabled && 'disabled',
                ]}
                onClick={(e) => handleClick(e, item, options)}
              >
                <div class="cascader-menu-item-cont">{item?.label}</div>
                {item?.children?.length > 0 && (
                  <div class="cascader-menu-item-expand">
                    <Icon icon="ant-design:right-outlined" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      );
    }
    const _selectOption = arr?.find((item) => item.selected);

    return (
      <>
        {_menuElm(arr)}
        {_selectOption?.children?.length > 0 && renderMemu(_selectOption?.children)}
      </>
    );
  }
  function handleClick(e, option, options) {
    e?.stopPropagation();
    if (option?.disabled) return;
    options?.forEach((item) => {
      item.selected = item.value == option.value;
    });
    if (!(option?.children?.length > 0)) {
      curValue.value = fundNodeLevel(curOptions.value);
      emits('change', curValue.value);
      dropdownOpen.value = false;
    }
  }
  function renderSearchMenus() {
    return renderSearchMenu(filterOptions.value);
  }
  function renderSearchMenu(arr?: any[]) {
    function _menuElm(title, options) {
      if (options?.length > 0) {
        return options?.map((item, index) => {
          if (item?.children?.length > 0) {
            return _menuElm(title + (title && ' / ') + item?.label, item?.children);
          } else {
            return (
              <div class="px-2">
                {index == 0 && title}
                <div
                  onClick={() => handleClickSearch(title, item?.value)}
                  class="rounded cursor-pointer flex items-center justify-between py-1 px-2 cascader-menu-item"
                >
                  {item?.label}
                </div>
              </div>
            );
          }
        });
      }
    }
    return <>{_menuElm('', arr)}</>;
  }
  function handleClickSearch(title: any, value: any) {
    const _arr = title.split('/')?.map((item) => {
      return item.trim();
    });
    _arr.push(value);
    curValue.value = _arr;
    emits('change', curValue.value);
    dropdownOpen.value = false;
    searchInfo.value = '';
  }
  function menuStyleFn() {
    const _width = props.width == 'auto' ? slotCont.value?.offsetWidth : props.width;
    menuStyle.value = {
      width: parseInt(_width) + 'px',
    };
  }
  onMounted(() => {
    window.addEventListener('resize', menuStyleFn);
  });
  onUnmounted(() => {
    window.removeEventListener('resize', menuStyleFn);
  });
  function fundNodeLevel(arr: any[]) {
    const _level = [];
    const _selectItem = arr?.find((items) => {
      return items.selected;
    });
    _level.push(_selectItem.value);
    if (_selectItem?.children?.length > 0) {
      _level.push(...fundNodeLevel(_selectItem?.children));
    }
    return _level;
  }
  function removeSelected(arr: any[]) {
    arr?.forEach((item) => {
      item.selected = false;
      if (item?.children?.length > 0) {
        removeSelected(item?.children);
      }
    });
  }
</script>
<style lang="less">
  .cascader-pop {
    border-radius: 4px;
    background-color: @cascader-bg-color;
    box-shadow:
      0 6px 16px 0 rgb(0 0 0 / 8%),
      0 3px 6px -4px rgb(0 0 0 / 12%),
      0 9px 28px 8px rgb(0 0 0 / 5%);
  }

  .cascader-menus {
    display: flex;
    flex-wrap: nowrap;
    align-items: flex-start;

    .cascader-menu {
      flex-grow: 1;
      height: 180px;
      margin: 0;
      padding: 4px;
      overflow: auto;

      &-item {
        display: flex;
        flex-wrap: nowrap;
        align-items: center;
        padding: 5px 12px;
        overflow: hidden;
        transition: all 0.2s;
        border-radius: 4px;
        text-overflow: ellipsis;
        white-space: nowrap;
        cursor: pointer;

        &.active,
        &:hover {
          background: @cascader-menu-item-bg-color-hover;
        }

        &.disabled {
          background-color: unset;
          color: #64656c;
          cursor: not-allowed;
        }

        &-cont {
          flex: auto;
        }
      }
    }
  }

  .cascader-menu-item {
    &:hover {
      background: @cascader-menu-item-bg-color-hover;
    }
  }
</style>
