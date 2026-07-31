import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { riskLevelOptions, yesNoOptions2 } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';

export function getBasicColumns(cb?: Function): BasicColumn[] {
  return [
    {
      dataIndex: 'productName',
      title: '产品/账户',
      // ellipsis: true, // 是否自动省略过长的文本
      // width: 200, // 列的宽度
      customRender({ record }) {
        const _val = record?.productName + '/' + record?.accountCode;
        return record?.riskType != 'OTHER' ? _val : '- -';
      },
    },
    // {
    //   dataIndex: 'riskTypeDisplay',
    //   title: '类型',
    //   // width: 80,
    // },
    {
      dataIndex: 'riskLevel',
      title: '触发风险等级',
      // width: 100,
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
      dataIndex: 'action',
      title: '操作',
      width: 160,
      customRender: ({ text, record }) => {
        return (
          <div class="flex gap-4">
            {record?.riskType != 'OTHER' ? (
              <div
                class="text-[#EB6E2C] cursor-pointer"
                onClick={() => cb && cb({ type: 'jump', data: record })}
              >
                去处理
              </div>
            ) : (
              ''
            )}

            {record?.riskLevel != 'level4' && record?.riskLevel != 'level5' ? (
              <div
                class="text-[#2FB97B] cursor-pointer"
                onClick={() => cb && cb({ type: 'ignore', data: record })}
              >
                忽略
              </div>
            ) : null}
          </div>
        );
      },
    },
  ];
}
/**
 * 获取基础列配置的函数
 * @returns 返回一个包含表格列配置的数组
 */
export function getBasicColumns2(): BasicColumn[] {
  return [
    {
      dataIndex: 'productName', // 数据索引，对应数据源中的字段名
      title: '产品/账户', // 表格列的标题
      customRender({ record }) {
        // 自定义渲染函数
        return record?.productName + '/' + record?.accountCode; // 显示产品名称和账户代码的组合
      },
    },
    // {
    //   dataIndex: 'riskTypeDisplay', // 数据索引
    //   title: '类型',
    //   width: 80,
    // },
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
      width: 160,
      ellipsis: true,
      customRender: ({ text }) => <TextTranslate value={text} options={riskLevelOptions} />,
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
      width: 80,
      customRender: ({ text }) => text || '- -',
    },
  ];
}

export function getCloseColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'symbol',
      title: '标的',
      customRender: ({ text, record }) => {
        return <div class={record?.is_position ? 'text-[#2FB97B]' : ''}>{text}</div>;
      },
    },
    {
      dataIndex: 'expire_rest_days',
      title: '距离交割日剩余时间',
    },
  ];
}
