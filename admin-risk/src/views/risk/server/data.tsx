import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { serverStatusOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';

export function getBasicColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'name',
      title: '服务器名称',
    },
    {
      dataIndex: 'healthUrl',
      title: '检测路由',
    },
    {
      dataIndex: 'status',
      title: '状态',
      customRender: ({ text }) => (
        <TextTranslate value={text} type="dot" options={serverStatusOptions} />
      ),
    },
    {
      dataIndex: 'responseTime',
      title: '反应时间（毫秒）',
      customRender: ({ text }) => text || '- -',
    },
    {
      dataIndex: 'checkTime',
      title: '检测时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
  ];
}
