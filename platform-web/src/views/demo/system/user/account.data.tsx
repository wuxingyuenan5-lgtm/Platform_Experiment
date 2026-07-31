import { getAllRoleList, isAccountExist, getProducts } from '@/api/demo/system';
import { BasicColumn, FormSchema } from '@/components/Table';
import { formatToDateTime } from '@/utils/dateUtil';
import { yesNoOptions } from '@/utils/options/basicOptions';
import { TextTranslate } from '@/components/OptionTranslate';
import { h } from 'vue';
import { Switch } from 'ant-design-vue';

/**
 * transform mock data
 * {
 *  0: '华东分部',
 * '0-0': '华东分部-研发部'
 * '0-1': '华东分部-市场部',
 *  ...
 * }
 */
type CheckedType = boolean | string | number;

export const deptMap = (() => {
  const pDept = ['华东分部', '华南分部', '西北分部'];
  const cDept = ['研发部', '市场部', '商务部', '财务部'];

  return pDept.reduce((map, p, pIdx) => {
    map[pIdx] = p;

    cDept.forEach((c, cIndex) => (map[`${pIdx}-${cIndex}`] = `${p}-${c}`));

    return map;
  }, {});
})();

export const columns = function (onChangeStatus: any) {
  return [
    {
      title: '用户名',
      dataIndex: 'name',
      width: 120,
    },
    // {
    //   title: '昵称',
    //   dataIndex: 'nickname',
    //   width: 120,
    // },
    {
      title: '邮箱',
      dataIndex: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      width: 200,
    },
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
      title: '备注',
      dataIndex: 'remark',
      customRender({ text }) {
        return text || '--';
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
  ];
};
export const searchFormSchema: FormSchema[] = [
  {
    field: 'account',
    label: '用户名',
    component: 'Input',
    colProps: { span: 8 },
  },
  {
    field: 'nickname',
    label: '昵称',
    component: 'Input',
    colProps: { span: 8 },
  },
];

export const accountFormSchema: FormSchema[] = [
  {
    field: 'name',
    label: '用户名',
    component: 'Input',
    dynamicDisabled: true,
    componentProps: {
      autocomplete: 'new-password',
    },
  },
  {
    field: 'password',
    label: '密码',
    component: 'InputPassword',
    componentProps: {
      autocomplete: 'new-password',
    },
    required: true,
    ifShow: false,
  },
  {
    label: '角色',
    field: 'roleId',
    component: 'ApiSelect',
    componentProps: {
      api: getAllRoleList,
      resultField: 'data',
      labelField: 'name',
      valueField: 'id',
    },
    required: true,
  },
  {
    label: '邮箱',
    field: 'email',
    component: 'Input',
    required: true,
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
    label: '产品',
    field: 'productIds',
    component: 'ApiSelect',
    componentProps: {
      api: getProducts,
      resultField: 'data',
      labelField: 'productName',
      valueField: 'id',
      mode: 'multiple',
    } as any,
  },
  {
    label: '谷歌验证',
    field: 'code',
    component: 'Input',
    required: true,
  },
];
