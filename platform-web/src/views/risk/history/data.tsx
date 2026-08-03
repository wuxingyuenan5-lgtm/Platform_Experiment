import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { platformOptions, metricCodeOptions, dataTypeOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';

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
    {
      dataIndex: 'dataType', // 数据索引
      title: '数据类型', // 表格列标题
      customRender: ({ text }) => <TextTranslate value={text} options={dataTypeOptions} />, // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'metricCode', // 数据索引
      title: '指标代码', // 表格列标题
      customRender: ({ text }) => <TextTranslate value={text} options={metricCodeOptions} />, // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'metricValue', // 数据索引
      title: '指标数', // 表格列标题
      customRender: ({ text }) => text ?? '- -',
    },
    {
      dataIndex: 'platform', // 数据索引
      title: '平台', // 表格列标题
      customRender: ({ text }) =>
        text ? <TextTranslate value={text} options={platformOptions} /> : '- -', // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'createdAt',
      title: '创建时间',
      width: 160,
      customRender: ({ text }) => formatToDateTime(text),
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
