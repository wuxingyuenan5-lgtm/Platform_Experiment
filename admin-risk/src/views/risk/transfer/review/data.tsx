import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { riskLevelOptions2, auditStatusOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import { formateNumStr } from '@/utils/formate';
import { FormSchema } from '@/components/Form';

export function getColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'transferTypeDisplay',
      title: '调拨模式',
    },
    {
      dataIndex: 'fromAccountId',
      title: '调拨账户/地址',
    },
    {
      dataIndex: 'amount',
      title: '调拨金额',
      customRender: ({ text }) => formateNumStr(text),
    },
    {
      title: '划转币种',
      dataIndex: 'currency',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转出交易所',
      dataIndex: 'fromAccountExchange',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转出账户ID',
      dataIndex: 'fromAccountId',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转出账户类型',
      dataIndex: 'fromAccountType',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转出类型',
      dataIndex: 'fromType',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转入交易所',
      dataIndex: 'toAccountExchange',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转入账户ID',
      dataIndex: 'toAccountId',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转入账户类型',
      dataIndex: 'toAccountType',
      customRender: ({ text }) => text || '- -',
    },
    {
      title: '转入类型',
      dataIndex: 'toType',
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'userName',
      title: '发起人',
      width: 80,
    },
    {
      dataIndex: 'createTime',
      title: '发起时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'riskLevel',
      title: '调拨风险等级',
      width: 110,
      customRender: ({ text }) => (
        <TextTranslate type="dot" value={text} options={riskLevelOptions2} />
      ),
    },
    {
      dataIndex: 'riskDetail',
      title: '调拨风险详情',
    },
    {
      dataIndex: 'status',
      title: '审核状态',
      width: 80,
      customRender: ({ text }) => (
        <TextTranslate type="dot" value={text} options={auditStatusOptions} />
      ),
    },
    {
      dataIndex: 'reviewerName',
      title: '审核人',
      width: 80,
      customRender: ({ text }) => (text ? text : '- -'),
    },
    {
      dataIndex: 'reviewTime',
      title: '审核时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },

    {
      dataIndex: 'reviewComment',
      title: '备注',
      customRender: ({ text }) => (text ? text : '- -'),
    },
  ];
}

export const schemas: FormSchema[] = [
  {
    field: 'requestId',
    component: 'Input',
    label: '',
    show: false,
  },
  {
    field: 'action',
    component: 'Input',
    label: '',
    show: false,
  },
  {
    field: 'code',
    component: 'Input',
    required: true,
    label: '谷歌验证码',
  },
  {
    field: 'comment',
    component: 'InputTextArea',
    label: '备注',
  },
];
