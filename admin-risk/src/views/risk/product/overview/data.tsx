import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import {
  positionSideOptions,
  categoryTypeOptions,
  platformOptions,
} from '@/utils/options/basicOptions';
import { formateNumStr } from '@/utils/formate';
import { Tooltip } from 'ant-design-vue';
import { ref } from 'vue';

export function getPositionColumns(): BasicColumn[] {
  const _isCny = ref(true);
  function changeUnit() {
    _isCny.value = !_isCny.value;
  }
  return [
    {
      dataIndex: 'platform',
      title: '平台',
      customRender: ({ text }) => <TextTranslate value={text} options={platformOptions} />,
    },
    {
      dataIndex: 'checkCode',
      title: '账号',
    },
    {
      dataIndex: 'symbol',
      title: '标的名称',
    },
    {
      dataIndex: 'category',
      title: '标的类型',
      customRender: ({ text }) => <TextTranslate value={text} options={categoryTypeOptions} />,
    },
    {
      dataIndex: 'size',
      title: '持仓量',
      customRender: ({ text }) => formateNumStr(text),
    },
    {
      dataIndex: 'lastPrice',
      title: '最新价',
      customRender: ({ text }) =>
        formateNumStr(text, {
          decimals: 2,
          keepZero: true,
        }),
    },
    {
      dataIndex: 'avgPrice',
      title: '持仓均价',
      customRender: ({ text }) =>
        formateNumStr(text, {
          decimals: 2,
          keepZero: true,
        }),
    },
    {
      dataIndex: 'liqPrice',
      title: '预估强平价',
      customRender: ({ text }) =>
        formateNumStr(text, {
          decimals: 2,
          keepZero: true,
        }),
    },
    {
      dataIndex: 'quantity',
      title: '克重',
      customRender: ({ text }) => formateNumStr(text),
    },
    {
      dataIndex: 'positionValueCNY',
      customHeaderRender: () => (
        <Tooltip title="切换币种" placeholder="topLeft">
          <div onClick={changeUnit} class="cursor-pointer flex items-center gap-2px">
            仓位价值（{_isCny.value ? 'CNY' : 'USD'}）
          </div>
        </Tooltip>
      ),
      customRender: ({ text, record }) =>
        formateNumStr(_isCny.value ? text : record.positionValueUSD, {
          decimals: 2,
          keepZero: true,
        }),
    },
    {
      dataIndex: 'side',
      title: '持仓方向',
      customRender: ({ text }) => <TextTranslate value={text} options={positionSideOptions} />,
    },
  ];
}

export function getPositionFutureColumns(): BasicColumn[] {
  return [
    {
      title: '标的',
      dataIndex: 'exchange',
    },
    {
      title: '合约',
      dataIndex: 'symbol',
    },
    {
      dataIndex: 'volume',
      title: '持仓量',
      customRender: ({ text }) => formateNumStr(text),
    },
    {
      dataIndex: 'value',
      title: '仓位价值',
      customRender: ({ text }) =>
        text ? formateNumStr(text, { decimals: 2, keepZero: true }) : '- -',
    },
    {
      dataIndex: 'side',
      title: '持仓方向',
      customRender: ({ text }) => <TextTranslate value={text} options={positionSideOptions} />,
    },
  ];
}
