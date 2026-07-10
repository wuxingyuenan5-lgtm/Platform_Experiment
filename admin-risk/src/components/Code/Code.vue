<template>
  <div class="code-box">
    <Input
      v-for="(item, i) in inputRefCode"
      :key="i"
      :ref="item"
      :data-index="i"
      :maxlength="2"
      placeholder=""
      v-model:value="data[i]"
      style="width: 32px"
      @keyup="(e) => keydown(e?.key as KeyupType, i)"
      @keydown="(e) => keyup(e?.key as KeyupType, i)"
      @input="(e) => InputChange(e)"
    />
  </div>
</template>
<script lang="ts" setup>
  import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue';
  import { Input } from 'ant-design-vue';

  const emit = defineEmits(['change', 'enter']);
  enum KeyupType {
    left = 'ArrowLeft',
    right = 'ArrowRight',
    del = 'Backspace',
    enter = 'Enter',
  }
  const inputNum = 6;
  // @ts-ignore
  const inputRefCode: any[] = new Array(inputNum).fill(0).map(() => ref());
  const data = ref(new Array(inputNum));

  const code = computed(() => {
    const _code = data.value.join('');
    return _code;
  });
  watch(code, (newVal) => {
    emit('change', { code: newVal });
  });
  function clearAll() {
    data.value = new Array(inputNum);
  }

  function keydown(type: KeyupType, index: number) {
    switch (type) {
      case KeyupType.del:
        if (!data.value[index]) {
          inputRefCode?.[parseInt(index) - 1]?.value?.[0].focus();
        }
        break;
    }
  }
  function keyup(type: KeyupType, index: number) {
    switch (type) {
      case KeyupType.left:
        inputRefCode?.[index - 1]?.value?.[0].focus();
        break;
      case KeyupType.right:
        inputRefCode?.[index + 1]?.value?.[0].focus();
        break;
    }
  }
  function InputChange(e: any) {
    const _val = e.data,
      _targetVal = e.target.value;
    // 只取最后一位输入的值并且是数字
    if (/^\d$/.test(_val)) {
      if (_targetVal?.length > 1) {
        data.value[e.target.dataset.index] = _val;
      } else {
        data.value[e.target.dataset.index] = _targetVal;
      }
      if (_val) {
        nextTick(() => {
          if (e.target.dataset.index != inputNum - 1) {
            inputRefCode?.[parseInt(e.target.dataset.index) + 1].value?.[0].focus();
          } else {
            inputRefCode?.[inputNum - 1].value?.[0].blur();
          }
        });
      }
    } else {
      data.value[e.target.dataset.index] = '';
    }
  }
  defineExpose({ code, clearAll });
  onMounted(() => {
    setTimeout(() => {
      inputRefCode?.[0]?.value?.[0].focus();
    }, 0);
    window.addEventListener('keyup', keyEnter);
  });

  function keyEnter(e: any) {
    if (e?.key == 'Enter') {
      emit('enter');
    }
  }

  onUnmounted(() => {
    window.removeEventListener('keyup', keyEnter);
  });
</script>
<style lang="less" scoped>
  .code-box {
    margin-top: 32px;
    margin-bottom: 4px;

    .ant-input {
      padding-right: 8px;
      padding-left: 8px;
      border: 1px solid @control-bg;
      background-color: @control-bg;
      text-align: center;

      &:focus {
        border-color: @primary-color;
        box-shadow: unset;
      }
    }

    .ant-input + .ant-input {
      margin-left: 16px;
    }
  }
</style>
