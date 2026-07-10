<template>
  <div class="flex items-center">
    <FormItem
      v-bind="formProps"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
      :label="label"
      :name="field"
      ref="customformItem"
      :rules="handleRules()"
      :autoLink="false"
    >
      <div class="flex items-center whitespace-nowrap">
        <FormItemRest>
          <Input
            type="number"
            v-bind="compAttr"
            placeholder="请输入"
            v-model:value="model[_firstField]"
            @blur="
              () => {
                // @ts-ignore
                $refs.customformItem?.onFieldBlur?.();
              }
            "
          />
        </FormItemRest>
        <span class="mr-3 ml-3">~</span>
        <FormItemRest
          ><Input
            type="number"
            v-bind="compAttr"
            placeholder="请输入"
            v-model:value="model[_lastField]"
            @blur="
              () => {
                // @ts-ignore
                $refs.customformItem?.onFieldBlur?.();
              }
            "
        /></FormItemRest>
      </div>
    </FormItem>
    <Checkbox
      v-if="_checkField"
      v-bind="compAttr"
      v-model:checked="model[_checkField]"
      class="ml-2 whitespace-nowrap mb-6"
      >{{ checkBoxLabel }}</Checkbox
    >
  </div>
</template>
<script lang="ts" setup>
  import { defineProps, toRefs, ref, unref, computed, type Ref, watch } from 'vue';
  import { Input, Checkbox, FormItem, FormItemRest } from 'ant-design-vue';
  import { propTypes } from '@/utils/propTypes';
  import { type FormProps, type FormSchemaInner as FormSchema } from '../types/form';
  import { useItemLabelWidth } from '../hooks/useLabelWidth';
  import { Rule, RuleObject } from 'ant-design-vue/es/form';

  const emit = defineEmits(['field-value-change']);
  const props = defineProps({
    firstField: propTypes.string.def('firstVal'),
    lastField: propTypes.string.def('lastVal'),
    checkField: propTypes.string.def(''),
    checkBoxLabel: propTypes.string.def(''),
    schema: {
      type: Object as PropType<FormSchema>,
      default: () => ({}),
    },
    formProps: {
      type: Object as PropType<FormProps>,
      default: () => ({}),
    },
    model: {
      type: Object as PropType<Recordable>,
      default: () => ({}),
    },
  });
  const { schema, formProps, model } = toRefs(props) as {
    schema: Ref<FormSchema>;
    formProps: Ref<FormProps>;
    model: Ref<Recordable>;
  };
  watch(
    () => schema.value.defaultValue,
    () => {
      const _key1 = schema.value?.fields?.[0] || props.firstField;
      if (schema.value?.defaultValue?.length > 0) {
        model.value[_key1] = schema.value.defaultValue?.[0];
      }
      const _key2 = schema.value?.fields?.[1] || props.lastField;
      if (schema.value?.defaultValue?.length > 1) {
        model.value[_key2] = schema.value.defaultValue?.[1];
      }
    },
  );
  const _firstField = computed(() => {
    return schema.value?.fields?.[0] || props.firstField;
  });
  const _lastField = computed(() => {
    return schema.value?.fields?.[1] || props.lastField;
  });
  const _checkField = computed(() => {
    return schema.value?.fields?.[2] || props.checkField;
  });
  const compAttr = computed(() => {
    return {
      ...unref(formProps),
      allowClear: true,
    };
  });

  const { label, field } = schema.value;
  const itemLabelWidthProp = useItemLabelWidth(schema, formProps);
  const { labelCol, wrapperCol } = unref(itemLabelWidthProp);

  const customformItem: Ref<any> = ref();
  const validatorField = async (_rule?: Rule) => {
    let _isValid = false;
    if (
      // (!model.value[_firstField.value] && !model.value[_lastField.value]) ||
      Number(model.value[_firstField.value]) < Number(model.value[_lastField.value])
    ) {
      _isValid = true;
    }
    emit(
      'field-value-change',
      field,
      _isValid && model.value[_firstField.value] != ''
        ? [model.value[_firstField.value], model.value[_lastField.value]]
        : null,
    );
    return _isValid ? Promise.resolve() : Promise.reject('请输入正确范围格式');
  };
  function handleRules(): RuleObject[] {
    const { required = false } = schema.value;
    // console.log('handleRules', schema.value);

    let rules: RuleObject[] = [
      { required: required as any, validator: validatorField, trigger: 'blur' },
    ];
    return rules;
  }
</script>
