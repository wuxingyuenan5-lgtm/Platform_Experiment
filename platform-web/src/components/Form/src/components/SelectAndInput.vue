<template>
  <div class="flex items-center">
    <FormItem
      v-bind="formProps"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
      :label="label"
      :name="field"
    >
      <div class="flex">
        <Input.Group class="!flex" compact>
          <FormItemRest>
            <component class="min-w-28" :is="renderComponent" />
          </FormItemRest>
          <FormItemRest>
            <Input
              class="z-10"
              v-bind="compAttr"
              placeholder="请输入"
              v-model:value="model[_inputField]"
            />
          </FormItemRest>
        </Input.Group>
        <div class="flex items-center">
          <span class="ml-3 mr-1">或</span>
          <FormItemRest>
            <Checkbox
              v-if="_checkField"
              v-bind="compAttr"
              v-model:checked="model[_checkField]"
              class="ml-2 whitespace-nowrap"
              >{{ checkBoxLabel }}</Checkbox
            >
          </FormItemRest>
          <FormItemRest> <Input suffix="%" v-bind="compAttr" type="number" /></FormItemRest>
        </div>
      </div>
    </FormItem>
  </div>
</template>
<script lang="tsx" setup>
  import {
    defineProps,
    toRefs,
    unref,
    computed,
    defineComponent,
    type Ref,
    type Component,
  } from 'vue';
  import { Input, Checkbox, FormItem, FormItemRest, Select } from 'ant-design-vue';
  import { propTypes } from '@/utils/propTypes';
  import {
    type FormProps,
    type FormSchemaInner as FormSchema,
    type FormActionType,
  } from '../types/form';
  import { useItemLabelWidth } from '../hooks/useLabelWidth';
  import ApiSelect from './ApiSelect.vue';
  import { upperFirst } from 'lodash-es';
  import type { ComponentType } from '../types';
  import { isFunction } from '@/utils/is';
  import { isIncludeSimpleComponents } from '../helper';
  import type { TableActionType } from '@/components/Table';
  import { useI18n } from '@/hooks/web/useI18n';

  const { t } = useI18n();

  const props = defineProps({
    inputField: propTypes.string.def('inputVal'),
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
    formActionType: {
      type: Object as PropType<FormActionType>,
    },
    tableAction: {
      type: Object as PropType<TableActionType>,
    },
  });
  const { schema, formProps, model } = toRefs(props) as {
    schema: Ref<FormSchema>;
    formProps: Ref<FormProps>;
    model: Ref<Recordable>;
  };
  const _inputField = computed(() => {
    return schema.value?.fields?.[0] || props.inputField;
  });
  const _checkField = computed(() => {
    return schema.value?.fields?.[1] || props.checkField;
  });
  const componentMap = new Map<ComponentType | string, Component>();
  componentMap.set('Select', Select);
  componentMap.set('ApiSelect', ApiSelect);
  const compAttr: Recordable<any> = {
    ...unref(formProps),
    allowClear: true,
  };
  const { label, field } = schema.value;
  const itemLabelWidthProp = useItemLabelWidth(schema, formProps);
  const { labelCol, wrapperCol } = unref(itemLabelWidthProp);

  const getComponentsProps = computed(() => {
    const { schema, tableAction, model, formActionType } = props;
    let { componentProps = {} } = schema;
    if (isFunction(componentProps)) {
      componentProps = componentProps({ schema, tableAction, model, formActionType }) ?? {};
    }
    if (isIncludeSimpleComponents(schema.component)) {
      componentProps = Object.assign(
        { type: 'horizontal' },
        {
          orientation: 'left',
          plain: true,
        },
        componentProps,
      );
    }
    return componentProps as Recordable<any>;
  });
  function setFormModel(key: string, value: any) {
    model.value[key] = value;
    // emit('field-value-change', key, value, schema);
  }
  function renderComponent() {
    const { component, field, changeEvent = 'change', valueField } = props.schema;
    const eventKey = `on${upperFirst(changeEvent)}`;

    const on = {
      [eventKey]: (...args: Nullable<Recordable<any>>[]) => {
        const [e] = args;
        if (propsData[eventKey]) {
          propsData[eventKey](...args);
        }
        const target = e ? e.target : null;
        const value = target ? target.value : e;
        setFormModel(field, value);
      },
    };
    const Comp = componentMap.get(component) as ReturnType<typeof defineComponent>;

    const { size } = props.formProps;
    const propsData: Recordable<any> = {
      allowClear: true,
      size,
      placeholder: t('common.chooseText'),
      ...unref(getComponentsProps),
      disabled: props.formProps.disabled,
      readonly: props.formProps.readonly,
    };
    propsData.codeField = field;

    const bindValue: Recordable<any> = {
      [valueField || 'value']: props.model[field],
    };

    const compAttr: Recordable<any> = {
      ...propsData,
      ...on,
      ...bindValue,
    };
    return <Comp {...compAttr}></Comp>;
  }
  renderComponent();
</script>
