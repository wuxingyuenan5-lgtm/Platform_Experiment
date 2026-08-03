export const listSetting = {
  fetchSetting: {
    pageField: 'pageIndex',
    sizeField: 'pageSize',
    listField: 'data',
    totalField: 'total',
  },
  defaultPageSize: 10,
  defaultSize: 'middle',
  pageSizeOptions: ['10', '50', '80', '100'],
};
// const { table } = componentSetting;

const { pageSizeOptions, defaultPageSize, fetchSetting, defaultSize } = listSetting;

export const ROW_KEY = 'key';

// Optional display number per page;
export const PAGE_SIZE_OPTIONS = pageSizeOptions;

// Number of items displayed per page
export const PAGE_SIZE = defaultPageSize;

// Common interface field settings
export const FETCH_SETTING = fetchSetting;

// Default Size
export const DEFAULT_SIZE = defaultSize;

//  Default layout of table cells
export const DEFAULT_ALIGN = 'center';

export const INDEX_COLUMN_FLAG = 'INDEX';

export const ACTION_COLUMN_FLAG = 'ACTION';
