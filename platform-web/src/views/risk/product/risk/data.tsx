import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import {
  positionSideOptions,
  categoryTypeOptions,
  closeLogStatusOptions,
  closeTypeOptions,
  orderExecStrategyOptions,
  orderTypeOptions,
  orderStatusOptions3,
  targetOptions,
  directionOptions,
} from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { formateNumStr, formatNumberWithCommas } from '@/utils/formate';
import { useSymbolRisk } from '@/utils/options/useBasicOptions';
import GhostButton from '@/components/Button/src/GhostButton.vue';
import { FormSchema } from '@/components/Form';

export function getPositionColumns(cb: (data: any) => void): BasicColumn[] {
  // console.log('999----', options);
  const { options } = useSymbolRisk();

  return [
    {
      dataIndex: 'symbol',
      title: '标的名称',
      customRender: ({ text, record, index }) => (
        <div
          onClick={() => cb({ value: index, type: 'symbol' })}
          class="cursor-pointer hover:underline flex"
        >
          {text}-
          <TextTranslate value={record.category} options={categoryTypeOptions} />
        </div>
      ),
    },
    // {
    //   dataIndex: 'category',
    //   title: '标的类型',
    //   width: 80,
    //   customRender: ({ text }) => <TextTranslate value={text} options={categoryTypeOptions} />,
    // },
    {
      dataIndex: 'size',
      title: '持仓量',
      customRender: ({ text, record }) =>
        text ? text : record?.positionValue ? formateNumStr(record?.positionValue) : '- -',
    },
    {
      dataIndex: 'side',
      title: '持仓方向',
      ellipsis: true,
      customRender: ({ text }) => <TextTranslate value={text} options={positionSideOptions} />,
    },
    {
      dataIndex: 'size',
      title: '单边平仓',
      customRender: ({ text, record }) => {
        return (
          <GhostButton
            onClick={() => cb?.({ type: 'single', record })}
            size="small"
            color="error"
            noBorder
          >
            平仓
          </GhostButton>
        );
        // const _len = (text?.toString().split('.')[1] || '').length;
        // const _symbol = options.value?.find((item) => item.symbol == record.symbol);
        // // console.log('_symbol----', _symbol, _symbol?.lotSize?.toString().split('.'));

        // const _imputProps: any = {
        //   precision: _len,
        //   placeholder: '请输入平仓数量',
        // };
        // if (_symbol) {
        //   _imputProps.precision = (_symbol?.lotSize?.toString().split('.')[1] || '').length;
        //   // _imputProps.min = _symbol?.MinOrderQty * 1;
        //   _imputProps.step = _symbol?.lotSize * 1;
        // }
        // return (
        //   <SliderInput
        //     total={text}
        //     popTitle="单边平仓"
        //     imputProps={_imputProps}
        //     onSubmit={(val) => cb({ value: val, type: 'single', record })}
        //   />
        // );
      },
    },
  ];
}
export function getPositionColumnsSh(cb: (data: any) => void): BasicColumn[] {
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
      title: '数量（手）',
      dataIndex: 'volume',
      ellipsis: true,
      customRender: ({ text }) =>
        text ? formateNumStr(text, { decimals: 2, keepZero: true }) : '- -',
    },
    {
      dataIndex: 'side',
      title: '持仓方向',
      ellipsis: true,
      customRender: ({ text }) => <TextTranslate value={text} options={positionSideOptions} />,
    },
    {
      dataIndex: 'volume',
      title: '单边平仓',
      width: 320,
      customRender: ({ text, record }) => {
        return record?.exchange == '沪金' ? (
          <GhostButton onClick={() => cb?.(record)} size="small" color="error" noBorder>
            平仓
          </GhostButton>
        ) : (
          // <SliderInput
          //   total={text}
          //   popTitle="单边平仓"
          //   imputProps={{ precision: 0, placeholder: '请输入平仓数量' }}
          //   onSubmit={(val) => cb({ value: val, type: 'single', record })}
          // />
          ''
        );
      },
    },
  ];
}

export function getLogColumns(): BasicColumn[] {
  const { options } = useSymbolRisk();

  return [
    {
      dataIndex: 'accountCode',
      title: '账号代码',
    },
    {
      dataIndex: 'executionParams',
      title: '标的名称',
      customRender: ({ text }) => text?.symbol || '- -',
    },
    {
      dataIndex: 'executionParams',
      title: '标的类型',
      width: 100,
      customRender: ({ text }) => (
        <TextTranslate value={text?.category} options={categoryTypeOptions} />
      ),
    },
    {
      dataIndex: 'executionParams',
      title: '平仓类型',
      width: 100,
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
      width: 100,
      customRender: ({ text }) => (
        <TextTranslate value={text?.side} options={positionSideOptions} />
      ),
    },
    {
      dataIndex: 'executionParams',
      title: '执行策略',
      width: 100,
      customRender: ({ text }) => text?.timeInForce || '- -',
    },
    {
      dataIndex: 'status',
      title: '状态',
      width: 100,
      customRender({ text }) {
        return <TextTranslate options={closeLogStatusOptions} value={text} />;
      },
    },
    {
      dataIndex: 'startTime',
      title: '开始时间',
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

// 单边平仓-BALANCE
export function getSingleCloseColumns(): FormSchema[] {
  return [
    // {
    //   field: 'deviation',
    //   component: 'Input',
    //   defaultValue: 20,
    //   componentProps: {
    //     size: 'large',
    //   },
    //   required: true,
    //   label: <div class="color-secondary text-xs">滑点</div>,
    //   rulesMessageJoinLabel: false,
    // },
    {
      field: 'percentage',
      component: 'Slider',
      defaultValue: 0.1,
      componentProps: {
        marks: {
          0: '0',
          0.25: '0.25%',
          0.5: '0.5%',
          0.75: '0.75%',
          1: '1%',
        },
        min: 0,
        max: 1,
        step: 0.01,
        defaultValue: 0,
        class: 'w-300px margin-auto',
      },
      required: true,
      label: <div class="color-secondary text-xs">百分比偏移</div>,
      rulesMessageJoinLabel: false,
    },
    {
      field: 'quantity',
      component: 'Input',
      required: true,
      label: <div class="color-secondary text-xs">平仓数量</div>,
      colSlot: 'quantitySlot',
    },
    {
      field: 'timeInForce',
      component: 'Select',
      required: true,
      defaultValue: 'IOC',
      label: <div class="color-secondary text-xs">执行类型</div>,
      componentProps: {
        size: 'large',
        options: orderExecStrategyOptions,
        popupClassName: 'z-9999',
        allowClear: false,
      },
      rulesMessageJoinLabel: false,
    },
    {
      field: 'code',
      component: 'Input',
      componentProps: {
        size: 'large',
      },
      required: true,
      label: <div class="color-secondary text-xs">谷歌验证</div>,
      rulesMessageJoinLabel: false,
    },
  ];
}

// 单边平仓-SHFE
export function getSingleCloseSHFEColumns(): FormSchema[] {
  return [
    {
      field: 'quantity',
      component: 'Input',
      required: true,
      label: <div class="color-secondary text-xs">平仓数量</div>,
      colSlot: 'quantitySlot',
    },
    {
      field: 'code',
      component: 'Input',
      required: true,
      label: <div class="color-secondary text-xs">谷歌验证</div>,
      rulesMessageJoinLabel: false,
    },
  ];
}

// 单边平仓-MT5
export function getSingleCloseMt5Columns(): FormSchema[] {
  return [
    {
      field: 'quantity',
      component: 'Input',
      required: true,
      label: <div class="color-secondary text-xs">平仓数量</div>,
      colSlot: 'quantitySlot',
    },
    {
      field: 'code',
      component: 'Input',
      required: true,
      label: <div class="color-secondary text-xs">谷歌验证</div>,
      rulesMessageJoinLabel: false,
    },
  ];
}
// 当前订单-BALANCE
export function getCurrentOrderSchemas() {
  return [
    {
      dataIndex: 'symbol',
      title: '标的',
    },
    {
      dataIndex: 'price',
      customRender: ({ text }) => (text ? formatNumberWithCommas(text) : '- -'),
      title: '订单价格',
    },
    {
      dataIndex: 'orderType',
      title: '订单类型',
      customRender: ({ text }) => <TextTranslate value={text} options={orderTypeOptions} />,
    },
    {
      dataIndex: 'qty',
      title: '成交/总量',
      customRender({ text, record }) {
        return text != 0 ? record?.cumExecQty + '/' + text : '0';
      },
    },
    {
      dataIndex: 'side',
      title: '方向',
      customRender: ({ text }) => <TextTranslate value={text} options={positionSideOptions} />,
    },
    {
      dataIndex: 'orderStatus',
      title: '状态',
      customRender: ({ text }) => <TextTranslate value={text} options={orderStatusOptions3} />,
    },
    {
      title: '创建时间',
      dataIndex: 'createdTime',
      width: 150,
      customRender({ text }) {
        return text ? formatToDateTime(Number(text)) : '- -';
      },
    },
  ];
}

// 计算器
export function getCalculatorColumns(): FormSchema[] {
  return [
    {
      field: 'direction',
      component: 'Select',
      required: true,
      label: '方向',
      componentProps: {
        options: directionOptions,
        popupClassName: 'z-9999',
      },
      colSlot: 'directionSlot',
    },
    {
      field: 'qty',
      component: 'Input',
      required: true,
      label: '数量',
      colSlot: 'qtySlot',
    },
    {
      field: 'symbol',
      component: 'Select',
      required: true,
      defaultValue: 'AU',
      label: '品种',
      componentProps: {
        options: targetOptions,
        popupClassName: 'z-9999',
        allowClear: false,
      },
    },
  ];
}
