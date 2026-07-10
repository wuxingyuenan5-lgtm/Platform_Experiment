import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import {
  closeLogStatusOptions,
  categoryTypeOptions,
  closeTypeOptions,
  positionSideOptions,
} from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { FormSchema } from '@/components/Form';
import { Popover } from 'ant-design-vue';
import { useSymbolRisk } from '@/utils/options/useBasicOptions';
import { formateNumStr } from '@/utils/formate';

export function getColumns(): BasicColumn[] {
  const { options } = useSymbolRisk();

  return [
    {
      dataIndex: 'id',
      title: 'ID',
      width: 60,
    },
    {
      dataIndex: 'productName',
      title: '产品名称',
    },
    {
      dataIndex: 'accountCode',
      title: '账号代码',
    },
    {
      dataIndex: 'executionParams',
      title: '标的名称',
      ellipsis: true,
      customRender: ({ text }) => text?.symbol || '- -',
    },
    {
      dataIndex: 'executionParams',
      title: '标的类型',
      width: 80,
      customRender: ({ text }) => (
        <TextTranslate value={text?.category} options={categoryTypeOptions} />
      ),
    },
    {
      dataIndex: 'executionParams',
      title: '平仓类型',
      width: 80,
      customRender: ({ text }) => (
        <TextTranslate value={text?.closeType} options={closeTypeOptions} />
      ),
    },
    {
      dataIndex: 'executionParams',
      title: '平仓数量',
      customRender: ({ text, record }) => {
        const _symbol = options.value?.find((item) => item.symbol == record.symbol);
        if (_symbol) {
          const _len = (_symbol?.lotSize?.toString().split('.')[1] || '').length;
          // console.log('_len----', _len, _symbol);
          return (text?.quantity * 1)?.toFixed(_len) || '- -';
        }
        return text?.quantity || '- -';
      },
    },
    {
      dataIndex: 'executionParams',
      title: '平仓方向',
      width: 80,
      customRender: ({ text }) => (
        <TextTranslate value={text?.side} options={positionSideOptions} />
      ),
    },
    {
      dataIndex: 'executionParams',
      title: '执行策略',
      width: 80,
      customRender: ({ text }) => text?.timeInForce || '- -',
    },
    {
      dataIndex: 'status',
      title: '状态',
      width: 80,
      customRender({ text }) {
        return <TextTranslate options={closeLogStatusOptions} value={text} />;
      },
    },
    {
      dataIndex: 'startTime',
      title: '开始时间',
      ellipsis: true,
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'exchangeRate',
      title: '汇率',
      customRender: ({ text }) => (text ? formateNumStr(text) : '- -'),
    },
    {
      dataIndex: 'premium',
      title: '溢价',
      customRender: ({ text }) => (text ? formateNumStr(text) : '- -'),
    },
    {
      dataIndex: 'errorMessage',
      title: '错误信息',
      ellipsis: true,
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'createdBy',
      title: '创建者',
      width: 100,
    },
  ];
}
