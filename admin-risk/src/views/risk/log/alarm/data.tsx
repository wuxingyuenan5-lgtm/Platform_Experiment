import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { riskLevelOptions, yesNoOptions } from '@/utils/options/basicOptions';
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
    {
      dataIndex: 'riskLevel', // 数据索引
      title: '风险等级', // 表格列标题
      width: 100,
      customRender: ({ text }) => <TextTranslate value={text} options={riskLevelOptions} />, // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'title',
      title: '标题',
    },
    {
      dataIndex: 'content',
      ellipsis: true,
      title: '内容',
    },

    {
      dataIndex: 'isRead',
      title: '是否已读',
      width: 100,
      customRender: ({ text, record }) => {
        return text ? (
          <TextTranslate key="1" value={text} options={yesNoOptions} />
        ) : (
          <TextTranslate key="2" value={text} options={yesNoOptions} />
        );
      }, // 使用TextTranslate组件显示风险等级
    },
    {
      dataIndex: 'messageTypeDisplay',
      title: '警报类型',
      width: 100,
    },
    {
      dataIndex: 'receiverName',
      title: '接收者',
      width: 100,
    },
    {
      dataIndex: 'createTime',
      title: '创建时间',
      width: 200,
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
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
      title: '断开API类型',
    },
    {
      dataIndex: 'symbol',
      title: '断开时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
  ];
}
