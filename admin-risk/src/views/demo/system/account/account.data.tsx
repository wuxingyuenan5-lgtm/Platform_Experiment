import { getAllRoleList, isAccountExist, getProducts } from '@/api/demo/system';
import { BasicColumn, FormSchema } from '@/components/Table';
import { formatToDateTime } from '@/utils/dateUtil';
import { platformOptions } from '@/utils/options/basicOptions';
import { TextTranslate } from '@/components/OptionTranslate';

/**
 * transform mock data
 * {
 *  0: '华东分部',
 * '0-0': '华东分部-研发部'
 * '0-1': '华东分部-市场部',
 *  ...
 * }
 */
export const deptMap = (() => {
  const pDept = ['华东分部', '华南分部', '西北分部'];
  const cDept = ['研发部', '市场部', '商务部', '财务部'];

  return pDept.reduce((map, p, pIdx) => {
    map[pIdx] = p;

    cDept.forEach((c, cIndex) => (map[`${pIdx}-${cIndex}`] = `${p}-${c}`));

    return map;
  }, {});
})();

export const columns: BasicColumn[] = [
  {
    title: '账号',
    dataIndex: 'checkCode',
  },
  // {
  //   title: '账号类型',
  //   dataIndex: 'checkCodeType',
  // },
  {
    title: '产品名称',
    dataIndex: 'productName',
  },
  {
    title: '平台',
    dataIndex: 'platform',
    customRender: ({ text }) => <TextTranslate value={text} options={platformOptions} />,
  },
  {
    title: '排序',
    dataIndex: 'sortOrder',
  },
  {
    title: '更新时间',
    dataIndex: 'updateTime',
    width: 180,
    customRender({ text }) {
      return text ? formatToDateTime(text) : '- -';
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
    label: '账号',
    field: 'checkCode',
    component: 'Input',
    required: true,
  },
  {
    label: '产品名称',
    field: 'productId',
    component: 'ApiSelect',
    required: true,
    componentProps: {
      api: getProducts,
      resultField: 'data',
      labelField: 'productName',
      valueField: 'id',
    },
  },
  // {
  //   label: '账号类型',
  //   field: 'productType',
  //   component: 'Input',
  //   required: true,
  // },
  // {
  //   label: '产品名称',
  //   field: 'productName',
  //   component: 'Input',
  //   required: true,
  // },
  {
    label: '平台',
    field: 'platform',
    component: 'Select',
    required: true,
    componentProps: {
      options: platformOptions,
    },
  },
  {
    label: '排序',
    field: 'sortOrder',
    component: 'Input',
    required: true,
  },
  {
    label: '谷歌验证',
    field: 'code',
    component: 'Input',
    required: true,
  },
];
