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
      title: '操作类型',
    },
    {
      dataIndex: 'symbol',
      title: '切断产品',
    },
    {
      dataIndex: 'symbol',
      title: '操作IP',
    },
    {
      dataIndex: 'symbol',
      title: '操作时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'symbol',
      title: '操作人',
    },
  ];
}
