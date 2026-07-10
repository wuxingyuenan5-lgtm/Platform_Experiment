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
      title: '产品名称',
      dataIndex: 'productName',
    },
    {
      title: '产品代码',
      dataIndex: 'productCode',
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 50,
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
    // {
    //   title: '备注',
    //   dataIndex: 'remark',
    //   customRender({ text }) {
    //     return text || '--';
    //   },
    // },
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
    field: 'productName',
    label: '产品名称',
    required: true,
    component: 'Input',
  },
  {
    field: 'productCode',
    label: '产品代码',
    required: true,
    component: 'Input',
  },
  {
    field: 'sortOrder',
    label: '排序',
    required: true,
    component: 'InputNumber',
    componentProps: {
      class: 'w-full',
    },
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
