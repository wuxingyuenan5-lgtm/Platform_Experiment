import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { yesNoOptions2, riskLevelOptions, riskStatusOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { FormSchema } from '@/components/Form';

export function getProductColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'productName', // 数据索引，对应数据源中的字段名
      title: '产品/账户', // 表格列的标题
      ellipsis: true, // 是否自动省略过长的文本
      width: 200, // 列的宽度
      customRender({ record }) {
        // 自定义渲染函数
        return record?.productName + '/' + record?.accountCode; // 显示产品名称和账户代码的组合
      },
    },
    // {
    //   dataIndex: 'riskTypeDisplay', // 数据索引
    //   title: '类型',
    //   ellipsis: true,
    //   width: 100,
    // },
    {
      dataIndex: 'isProcessed',
      title: '状态',
      width: 80,
      customRender: ({ text }) => <TextTranslate value={text} options={riskStatusOptions} />,
    },
    {
      dataIndex: 'riskLevel', // 数据索引
      title: '触发风险等级', // 表格列标题
      width: 100,
      customRender: ({ text }) => <TextTranslate value={text} options={riskLevelOptions} />, // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'riskFactor', // 数据索引
      title: '风险因子', // 表格列标题
      ellipsis: true,
    },
    {
      dataIndex: 'initialTriggerData',
      title: '最初触发数据',
      ellipsis: true,
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'createTime',
      title: '最初触发时间',
      width: 160,
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'triggerData',
      title: '最新触发数据',
      ellipsis: true,
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
      width: 80,
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'isIgnored',
      title: '是否忽略',
      width: 80,
      customRender: ({ text }) => <TextTranslate value={text} options={yesNoOptions2} />, // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'processedData',
      title: '处理后因子数据',
      ellipsis: true,
      customRender: ({ text }) => (text ? JSON.stringify(text) : '- -'),
    },
    {
      dataIndex: 'processedTime',
      title: '处理时间',
      ellipsis: true,
      width: 160,
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'remarks',
      title: '备注',
      ellipsis: true,
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'processor',
      title: '处理人',
      ellipsis: true,
      width: 100,
      customRender: ({ text }) => text || '- -',
    },
  ];
}

export function getServerColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'symbol',
      title: '服务器编号',
    },
    {
      dataIndex: 'symbol',
      title: '产品类型',
    },
    {
      dataIndex: 'symbol',
      title: '断开API类型',
    },
    {
      dataIndex: 'symbol',
      title: '断开时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'symbol',
      title: '确认时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'symbol',
      title: '操作人',
    },
  ];
}
