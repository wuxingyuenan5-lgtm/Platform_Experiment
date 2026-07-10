import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { linkStatusOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { FormSchema } from '@/components/Form';

export function getColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'name',
      title: '产品',
    },
    {
      dataIndex: 'is_switch',
      title: '连接情况 ',
      customRender: ({ text }) => (
        <TextTranslate value={text} options={linkStatusOptions} type="dot" />
      ),
    },
  ];
}
