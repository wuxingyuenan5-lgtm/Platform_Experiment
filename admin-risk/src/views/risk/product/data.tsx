import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { riskLevelOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import { Popover } from 'ant-design-vue';

export function getBasicColumns(cb?: Function): BasicColumn[] {
  return [
    {
      dataIndex: 'productName',
      title: '产品/账户',
      customRender({ record }) {
        return record?.productName + '/' + record?.accountCode;
      },
    },
    // {
    //   dataIndex: 'riskTypeDisplay',
    //   title: '类型',
    // },
    {
      dataIndex: 'riskLevel',
      title: '触发风险等级',
      customRender: ({ text }) => <TextTranslate value={text} options={riskLevelOptions} />,
    },
    {
      dataIndex: 'riskFactor',
      title: '风险因子',
    },
    {
      dataIndex: 'initialTriggerData',
      title: '最初触发数据',
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'createTime',
      title: '最初触发时间',
      // width: 160,
      customRender: ({ text }) => formatToDateTime(text),
    },
    {
      dataIndex: 'triggerData',
      title: '最新触发数据',
      ellipsis: true,
      minWidth: 300,
      customRender: ({ text }) => JSON.stringify(text),
    },
    {
      dataIndex: 'triggerTime',
      title: '最新触发时间',
      width: 160,
      customRender: ({ text }) => formatToDateTime(text),
    },
    {
      dataIndex: 'triggerCount',
      title: '触发次数',
      customRender: ({ text }) => text || '- -',
    },
  ];
}
