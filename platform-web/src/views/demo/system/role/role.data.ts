import { BasicColumn, FormSchema } from '@/components/Table';
import { h } from 'vue';
import { Switch } from 'ant-design-vue';
import { setRoleStatus } from '@/api/demo/system';
import { useMessage } from '@/hooks/web/useMessage';
import { formatToDateTime } from '@/utils/dateUtil';

type CheckedType = boolean | string | number;
export const columns = function (onChangeStatus: any) {
  return [
    {
      title: '角色名称',
      dataIndex: 'name',
    },
    {
      title: '角色值',
      dataIndex: 'value',
    },
    // {
    //   title: '排序',
    //   dataIndex: 'orderNo',
    //   width: 50,
    // },
    {
      title: '状态',
      dataIndex: 'status',
      customRender: ({ record }) => {
        if (!Reflect.has(record, 'pendingStatus')) {
          record.pendingStatus = false;
        }
        return h(Switch, {
          checked: record.status,
          checkedChildren: '启用',
          unCheckedChildren: '停用',
          loading: record.pendingStatus,
          onChange(checked: CheckedType) {
            onChangeStatus(record);
          },
        });
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      width: 180,
      customRender({ text }) {
        return text ? formatToDateTime(text) : '- -';
      },
    },
    {
      title: '更新时间',
      width: 180,
      dataIndex: 'updateTime',
      customRender({ text }) {
        return text ? formatToDateTime(text) : '- -';
      },
    },
    {
      title: '备注',
      dataIndex: 'remark',
      customRender({ text }) {
        return text || '--';
      },
    },
  ];
};
export const searchFormSchema: FormSchema[] = [
  {
    field: 'roleNme',
    label: '角色名称',
    component: 'Input',
    colProps: { span: 8 },
  },
  {
    field: 'status',
    label: '状态',
    component: 'Select',
    componentProps: {
      options: [
        { label: '启用', value: '1' },
        { label: '停用', value: '0' },
      ],
    },
    colProps: { span: 8 },
  },
];

export const formSchema: FormSchema[] = [
  {
    field: 'name',
    label: '角色名称',
    required: true,
    component: 'Input',
  },
  {
    field: 'value',
    label: '角色值',
    required: true,
    component: 'Input',
  },
  {
    field: 'status',
    label: '状态',
    component: 'RadioButtonGroup',
    defaultValue: true,
    componentProps: {
      options: [
        { label: '启用', value: true },
        { label: '停用', value: false },
      ],
    },
  },
  {
    label: '备注',
    field: 'remark',
    component: 'InputTextArea',
  },
  {
    label: '谷歌验证',
    field: 'code',
    component: 'Input',
    required: true,
  },
  {
    label: ' ',
    field: 'menuIds',
    slot: 'menu',
  },
];
