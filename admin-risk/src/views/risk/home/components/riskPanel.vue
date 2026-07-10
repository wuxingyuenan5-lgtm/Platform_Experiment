<template>
  <PanelContainer :bg-type="bgType" :title="curRecord.title">
    <template #action>
      <div class="flex items-center">
        <div class="color-secondary text-[12px] mr-1">{{ curRecord?.createTime }}</div>
      </div>
    </template>
    <div v-if="curRecord?.platform == AccountType.BALANCE" class="px-4 pt-5 h-210px">
      <component :is="renderRiskNew(curRecord)" />
      <div class="h-5 mt-4 text-error truncate">
        <div v-for="itemMsg in curRecord.msg" :key="itemMsg">
          {{ itemMsg }}
        </div>
      </div>
    </div>
    <div v-else-if="curRecord?.platform == AccountType.SHFE" class="px-4 pt-5 h-210px">
      <component :is="renderRiskShfe(curRecord)" />
    </div>
    <div v-else class="px-4 pt-5 h-210px">
      <component :is="renderRiskMt5(curRecord)" />
    </div>
  </PanelContainer>
</template>
<script lang="tsx" setup>
  import { watch, ref, reactive, computed, VNodeChild, toRaw } from 'vue';

  import { SimpleContainer, PanelContainer } from '@/components/Container';
  import { AccountType } from '@/views/account/detail/type';
  import { riskLevelOptions } from '@/utils/options/basicOptions';
  import { formateNumStr } from '@/utils/formate';
  import { formatToDateTimeM } from '@/utils/dateUtil';
  import ProgressLevel from './progressLevel.vue';

  const props = defineProps({
    record: {
      type: Object,
      default: () => {},
    },
    bgType: {
      type: String,
      default: 'default',
      validator(value) {
        return ['default', 'gary'].includes(value as any);
      },
    },
  });
  const riskLevelMap = getRiskLevelMap();
  const msgImMap: any = {
    二级: 'IMR超过阈值0.8，请检查！',
    三级: 'IMR超过阈值1.0，请检查！',
  };
  const msgMmMap: any = {
    二级: 'MMR超过阈值0.7，请勿新增仓位，立即检查！',
    三级: 'MMR超过阈值0.8，请勿新增仓位，立即检查！',
  };
  const curRecord = computed(() => {
    const item = props.record;
    if (item?.platform == AccountType.BALANCE) {
      let _msg: any = [];
      // if (item.accountIMRateLevel == '二级' || item.accountIMRateLevel == '三级') {
      //   _msg.push(msgImMap[item.accountIMRateLevel]);
      // }
      // if (item.accountMMRateLevel == '二级' || item.accountMMRateLevel == '三级') {
      //   _msg.push(msgMmMap[item.accountMMRateLevel]);
      // }
      // const _total = item.longPosValue + item.shortPosValue;
      return {
        // longPos: Number((item.longPosValue / _total || 0) * 100).toFixed(2) + '%',
        // shortPos: Number((item.shortPosValue / _total || 0) * 100).toFixed(2) + '%',
        title: item.checkCode,
        imrLevel: item.accountIMRateLevel,
        imr: item.accountImRate,
        mmrLevel: item.accountMMRateLevel,
        mmr: item.accountMmRate,
        msg: _msg,
        createTime: item.createTime ? formatToDateTimeM(item.createTime) : '',
        platform: item.platform,
        equity: item.equity,
        leverRatio: item.leverRatio,
      };
    } else if (item?.platform == AccountType.SHFE) {
      return {
        balance: item.balance,
        equity: item.available,
        title: item.checkCode,
        cont: item.leverageRatio,
        riskLevel: item.riskLevel,
        riskRatio: item.riskRatio,
        createTime: item.createTime ? formatToDateTimeM(item.createTime) : '',
        platform: item.platform,
        leverRatio: item.leverRatio,
        levelList: item?.levelList || [],
      };
    } else if (item?.platform == AccountType.MT5) {
      return {
        equity: item.equity,
        marginFree: item.marginFree,
        title: item.checkCode,
        cont: item.marginLevel,
        riskLevel: item.riskLevel,
        createTime: item.createTime ? formatToDateTimeM(item.createTime) : '',
        platform: item.platform,
        leverRatio: item.leverRatio,
        levelList: item?.levelList || [],
      };
    }
    // 添加默认返回值
    return {
      equity: '',
      title: '',
      cont: '',
      riskLevel: '',
      riskRatio: '',
      createTime: '',
      platform: AccountType.BALANCE,
      leverRatio: 0,
    };
  });
  function renderRiskNew(data: any) {
    const _itemImr = riskLevelMap[data?.imrLevel];
    const _itemMmr = riskLevelMap[data?.riskLevel];
    return (
      <>
        {renderProgress({
          leftTitle: <div class="color-secondary text-xs">IMR</div>,
          rightTitle: (
            <div
              class="text-xs"
              style={{
                color: _itemImr?.color || '#2FB97BFF',
              }}
            >
              {/* {_itemImr?.levlel}&nbsp; */}
              {Number(data?.imr * 100 || 0).toFixed(2) + '%'}
            </div>
          ),
          strokeColor: _itemImr?.color || '#2FB97BFF',
          percent: Number(data?.imr * 100 || 0).toFixed(2) + '%',
        })}
        <div class="my-4">
          {renderProgress({
            leftTitle: <div class="color-secondary text-xs">MMR</div>,
            rightTitle: (
              <div
                class="text-xs"
                style={{
                  color: _itemMmr?.color || '#2FB97BFF',
                }}
              >
                {/* {_itemMmr?.levlel}&nbsp; */}
                {Number(data?.mmr * 100 || 0).toFixed(2) + '%'}
              </div>
            ),
            strokeColor: _itemMmr?.color || '#2FB97BFF',
            percent: Number(data?.mmr * 100 || 0).toFixed(2) + '%',
          })}
        </div>
        <div class="flex items-center justify-between  mt-3">
          <div class="color-secondary ">总净值（USD）</div>
          <div class="text-lg">{formateNumStr(data?.equity, { decimals: 2 })}</div>
        </div>
        {data?.leverRatio && (
          <div class="flex items-center justify-between  mt-3">
            <div class="color-secondary ">名义杠杆率</div>
            <div class="text-lg">{data?.leverRatio || 0}%</div>
          </div>
        )}
      </>
    );
  }
  function renderRiskMt5(data: any) {
    const _itemColor = riskLevelMap[data?.riskLevel];
    console.log('renderRiskMt5-----', data?.levelList);

    return () => (
      <>
        <div class="flex flex-col h-full">
          <ProgressLevel
            reverse={true}
            value={data?.cont || 0}
            levelList={data?.levelList}
            showLevel={(data?.cont || 0) > 50}
          ></ProgressLevel>
          <div class="flex items-center justify-between  mt-6">
            <div class="color-secondary ">预付款维持率</div>
            <div
              class="text-lg"
              style={{
                color: _itemColor?.color || '',
              }}
            >
              {(data?.cont * 1).toFixed(2) || '0'}%
            </div>
          </div>
          <div class="flex items-center justify-between  mt-4">
            <div class="color-secondary ">权益（USD）</div>
            <div>{formateNumStr(data?.equity, { decimals: 2 })}</div>
          </div>
          <div class="flex items-center justify-between  mt-4">
            <div class="color-secondary ">可用预付款（USD）</div>
            <div>{formateNumStr(data?.marginFree, { decimals: 2 })}</div>
          </div>
          {data?.leverRatio && (
            <div class="flex items-center justify-between  mt-4">
              <div class="color-secondary ">名义杠杆率</div>
              <div>{data?.leverRatio || 0}%</div>
            </div>
          )}
        </div>
      </>
    );
  }
  function renderRiskShfe(data: any) {
    const _itemColor = riskLevelMap[data?.riskLevel];
    return () => (
      <>
        <div class="flex flex-col h-full">
          {/* {renderRiskLevel(data)} */}
          <ProgressLevel value={data?.riskRatio || 0} levelList={data?.levelList}></ProgressLevel>
          <div class="flex items-center justify-between  mt-6">
            <div class="color-secondary ">资金使用率</div>
            <div
              class="text-lg"
              style={{
                color: _itemColor?.color || '',
              }}
            >
              {(data?.riskRatio * 100 || 0).toFixed(2)}%
            </div>
          </div>
          <div class="flex items-center justify-between  mt-4">
            <div class="color-secondary ">权益（CNY）</div>
            <div>{formateNumStr(data?.balance, { decimals: 2 })}</div>
          </div>
          <div class="flex items-center justify-between  mt-4">
            <div class="color-secondary ">可用资金（CNY）</div>
            <div>{formateNumStr(data?.equity, { decimals: 2 })}</div>
          </div>
          {data?.leverRatio && (
            <div class="flex items-center justify-between  mt-4">
              <div class="color-secondary ">名义杠杆率</div>
              <div>{data?.leverRatio || 0}%</div>
            </div>
          )}
        </div>
      </>
    );
  }
  // 分段式等级
  function renderRiskLevel(data: any) {
    const _levelCount = riskLevelOptions.length;
    const _itemColor = riskLevelMap[data?.riskLevel];
    const _index = _itemColor?.index || 0;
    console.log('renderRiskLevel-----', _levelCount);

    return (
      <div class="flex items-center w-full gap-2">
        {new Array(_levelCount).fill(0).map((item, index) => {
          return (
            <div
              class="control-bg h-1 flex-1"
              style={{
                backgroundColor: index <= _index ? _itemColor?.color : '',
              }}
            ></div>
          );
        })}
      </div>
    );
  }
  interface ProgressConfig {
    bg?: string;
    strokeColor: string;
    leftTitle: string | VNodeChild | JSX.Element;
    rightTitle: string | VNodeChild | JSX.Element;
    percent: string;
  }
  function renderProgress(config?: ProgressConfig) {
    return (
      <div class="progress">
        <div class="progress_title">
          {config?.leftTitle}
          {config?.rightTitle}
        </div>
        <div class="progress_stroke" style={{ backgroundColor: config?.bg }}>
          <div
            class="progress_stroke_fill"
            style={{
              width: config?.percent,
              backgroundColor: config?.strokeColor,
            }}
          ></div>
        </div>
      </div>
    );
  }
  // 整理riskLevelMap数据
  function getRiskLevelMap() {
    const _riskLevelMap: any = {};
    riskLevelOptions.forEach((item: any, i) => {
      _riskLevelMap[item.grade] = {
        color: item.color,
        percent: 0.2 * i,
        levlel: item.label,
        index: i,
      };
      _riskLevelMap[item.label] = {
        color: item.color,
        percent: 0.2 * i,
        levlel: item.label,
        index: i,
      };
    });
    return _riskLevelMap;
  }
</script>
<style lang="less" scoped>
  :deep(.slick-slide) {
    height: 280px;
    overflow: hidden;
  }

  :deep(.slick-arrow.custom-slick-arrow::before) {
    display: none;
  }

  .custom-slick-arrow {
    z-index: 1;
    width: 32px;
    height: 32px;
    transition: ease all 0.3s;
    opacity: 0.2;
    background-color: #1f2d3d1c;
    color: #fff;
    font-size: 32px;

    &:hover {
      opacity: 0.5;
      color: #fff;
    }
  }

  .risk-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: @text-color-secondary;

    .title {
      font-size: 14px;
      font-weight: bold;
    }
  }

  .progress {
    font-size: 14px;

    &_title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding-bottom: 2px;
    }

    &_stroke {
      display: flex;
      height: 4px;
      overflow: hidden;
      border-radius: 4px;
      background-color: #ddd;

      &_fill {
        border-right: 1px solid @component-background;
        border-radius: 4px;
      }
    }
  }
</style>
