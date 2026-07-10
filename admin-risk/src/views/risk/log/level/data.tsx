import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { positionSideOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { FormSchema } from '@/components/Form';

export function getColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'symbol',
      title: '账户编号',
    },
    {
      dataIndex: 'symbol',
      title: '产品类型',
    },
    {
      dataIndex: 'symbol',
      title: '标的名称',
    },
    {
      dataIndex: 'symbol',
      title: '仓位方向',
    },
    {
      dataIndex: 'symbol',
      title: '平仓数量',
    },
    {
      dataIndex: 'symbol',
      title: '平仓价格',
    },
    {
      dataIndex: 'symbol',
      title: '平仓时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'symbol',
      title: '操作人',
    },
  ];
}
