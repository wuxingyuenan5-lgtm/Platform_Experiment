<template>
  <section class="cross-asset-screening" aria-label="跨资产筛选">
    <header class="screening-heading"
      ><div><h2>跨资产筛选</h2></div
      ><div class="screening-controls"
        ><button :disabled="loading" @click="load">{{ loading ? '读取中…' : '重新读取' }}</button
        ><button v-if="tab === 'matrix'" :disabled="!archive" @click="openChart(symbol)"
          >打开图表</button
        ></div
      ></header
    >
    <p v-if="error" role="alert" class="screening-warning"
      >{{ error }} <button @click="load">重试</button></p
    >
    <p v-if="notice" role="status" class="screening-notice"
      >{{ notice }} <button aria-label="关闭提示" @click="notice = ''">×</button></p
    >
    <p v-if="loading && !archive" role="status">正在读取跨资产行情与趋势…</p>
    <template v-if="archive && archiveInfo">
      <nav class="screening-tabs" aria-label="跨资产研究视图"
        ><button
          v-for="item in tabs"
          :key="item.key"
          :aria-pressed="tab === item.key"
          @click="tab = item.key"
          >{{ item.label }}</button
        ></nav
      >
      <WorkbookScreener
        v-if="archiveInfo.workbookSnapshot"
        v-show="tab === 'workbook'"
        :snapshot="archiveInfo.workbookSnapshot"
      />
      <section v-else-if="tab === 'workbook'" class="screening-card">
        <p role="alert">标的目录暂无法读取。</p>
        <button @click="tab = 'matrix'">查看趋势矩阵</button>
      </section>
      <div v-if="tab !== 'workbook'" class="screening-source"
        ><strong>{{ imported ? '本地导入行情' : '历史行情归档' }}</strong
        ><span
          >采集时间 {{ timestamp(archive.generatedAt) }} · {{ assets.length }}个标的 /
          {{ archive.series.length }}组原生周期 · 非实时行情</span
        ></div
      >
      <div
        v-if="tab === 'matrix' || tab === 'signals'"
        class="screening-metrics"
        aria-label="全观察池趋势分布"
      >
        <button
          v-for="item in structureOptions"
          :key="item.key"
          :aria-pressed="structure === item.key"
          :aria-label="item.label + '筛选'"
          @click="toggleStructure(item.key)"
          ><span>{{ item.label }}<small>全观察池</small></span
          ><strong>{{ counts[item.key] }}</strong></button
        >
      </div>
      <template v-if="tab === 'matrix' || tab === 'signals'">
        <section class="screening-card">
          <div class="screening-controls">
            <label class="screening-search"
              >搜索<input v-model="query" placeholder="代码、名称或分类"
            /></label>
            <label
              >资产类型<select aria-label="资产类型" v-model="kind"
                ><option value="all">全部</option
                ><option value="stock">个股</option
                ><option value="etf">ETF</option></select
              ></label
            >
            <label
              >范围<select aria-label="范围" v-model="scope"
                ><option value="all">全部标的</option
                ><option value="covered">已覆盖</option
                ><option value="holdings">备份持仓</option
                ><option value="sp500">标普500</option
                ><option value="ndx">纳斯达克100</option
                ><option value="curated">精选个股</option></select
              ></label
            >
            <label
              >结构<select aria-label="结构" v-model="structure"
                ><option value="all">全部状态</option
                ><option value="bull">四周期偏多</option
                ><option value="bear">四周期偏空</option
                ><option value="conflict">周期分歧</option
                ><option value="short">历史待验证</option></select
              ></label
            >
            <label
              >自选清单<select aria-label="自选清单" v-model="activeWatchlist"
                ><option value="">全部清单</option
                ><option v-for="list in watchlists" :key="list.id" :value="list.id"
                  >{{ list.name }}（{{ list.symbols.length }}）</option
                ></select
              ></label
            ><button @click="resetFilters">重置筛选</button>
          </div>
          <details
            ><summary>行业、分类与市值</summary
            ><div class="screening-controls screening-asset-options">
              <label
                >个股行业<select v-model="assetScreen.sectors" multiple aria-label="个股行业"
                  ><option v-for="s in sectors" :key="s">{{ s }}</option></select
                ></label
              >
              <label
                >个股分类<select v-model="assetScreen.industries" multiple aria-label="个股分类"
                  ><option v-for="s in industries" :key="s">{{ s }}</option></select
                ></label
              >
              <label
                >ETF分类<select v-model="assetScreen.etfs" multiple aria-label="ETF分类"
                  ><option v-for="s in etfCategories" :key="s">{{ s }}</option></select
                ></label
              >
              <label
                >最低市值（亿美元）<input v-model="assetScreen.min" type="number" min="0" /></label
              ><label
                >最高市值（亿美元）<input v-model="assetScreen.max" type="number" min="0"
              /></label>
              <label
                ><input v-model="assetScreen.includeUnknown" type="checkbox" />包含未知市值</label
              ><label
                ><input v-model="assetScreen.includeStale" type="checkbox" />包含旧观测值</label
              ><label
                ><input v-model="assetScreen.keepEtfs" type="checkbox" />市值筛选保留ETF</label
              > </div
            ><p class="screening-muted"
              >市值观测日 {{ caps?.date || '—' }} ·
              {{ caps?.method }}；ETF不以基金规模替代公司市值。</p
            ><p v-if="capRangeError(assetScreen)" role="alert">{{
              capRangeError(assetScreen)
            }}</p></details
          >
          <div class="screening-presets"
            ><button
              v-for="preset in TREND_PRESETS"
              :key="preset.id"
              @click="applyPreset(preset)"
              >{{ preset.name }}</button
            ></div
          >
          <div v-if="presets.length" class="screening-presets"
            ><label
              >我的方案<select
                v-model="chosenPreset"
                aria-label="我的趋势方案"
                @change="useChosenPreset"
                ><option value="">选择方案</option
                ><option v-for="preset in presets" :key="preset.id" :value="preset.id">{{
                  preset.name
                }}</option></select
              ></label
            >
            <template v-if="chosenPreset"
              ><label
                >新名称<input
                  v-model="presetRename"
                  maxlength="40"
                  aria-label="趋势方案新名称" /></label
              ><button @click="renamePreset">重命名方案</button
              ><button @click="updatePreset">用当前条件更新方案</button></template
            >
            <span v-for="preset in presets" :key="preset.id"
              ><button @click="applyPreset(preset)">{{ preset.name }}</button
              ><button :aria-label="'删除方案' + preset.name" @click="removePreset(preset.id)"
                >×</button
              ></span
            ></div
          >
        </section>
        <TrendFilters
          :filters="trendFilters"
          :sort="sort"
          @change="changeTrend"
          @reset="clearTrend"
          @save="savePreset"
        />
        <div v-if="activeFilters.length" class="screening-filter-chips" aria-label="已选筛选条件"
          ><button
            v-for="item in activeFilters"
            :key="item.key"
            :aria-label="'清除' + item.label"
            @click="item.clear()"
            >{{ item.label }} <span aria-hidden="true">×</span></button
          ></div
        >
        <div class="screening-results"
          ><strong>{{ rows.length }}个符合条件</strong
          ><span>主方向：零滞后趋势 · 原生已完成K线</span></div
        >
        <template v-if="tab === 'matrix'">
          <label><input v-model="matrixExpanded" type="checkbox" />显示均线参考体系</label>
          <details
            class="screening-card screening-watchlists"
            :open="!!activeWatchlist || picked.length > 0"
            ><summary
              >自选管理
              <span>{{
                picked.length ? '已选' + picked.length + '个标的' : '创建、编辑及批量添加'
              }}</span></summary
            ><div class="screening-controls"
              ><label
                >清单名称<input
                  v-model="listName"
                  maxlength="40"
                  placeholder="例如：跨资产观察" /></label
              ><button :disabled="!listName.trim()" @click="createList">创建清单</button
              ><button :disabled="!activeWatchlist || !listName.trim()" @click="renameList"
                >重命名</button
              ><button
                :disabled="!activeWatchlist || activeWatchlist === 'favorites'"
                @click="deleteList"
                >删除清单</button
              ><button :disabled="!activeWatchlist || !picked.length" @click="addPicked"
                >加入已选 {{ picked.length }}</button
              ><button :disabled="!activeWatchlist || !picked.length" @click="removePicked"
                >移出已选</button
              ><button :disabled="!activeWatchlist || !rows.length" @click="addAll"
                >加入筛选结果</button
              ></div
            ></details
          >
          <div class="screening-table" tabindex="0" role="region" aria-label="四周期趋势矩阵"
            ><table
              ><thead
                ><tr
                  ><th
                    ><input
                      type="checkbox"
                      aria-label="选中本页"
                      :checked="
                        pageRows.length > 0 && pageRows.every((s) => picked.includes(s.symbol))
                      "
                      @change="pickPage" /></th
                  ><th>标的 / 资产</th><th>分类 / 市值</th><th>排序转向</th
                  ><th v-for="f in FRAMES" :key="f">{{ FRAME_NAMES[f] }}</th
                  ><th>研究</th></tr
                ></thead
              ><tbody
                ><tr v-for="asset in pageRows" :key="asset.symbol"
                  ><td
                    ><input
                      v-model="picked"
                      type="checkbox"
                      :value="asset.symbol"
                      :aria-label="'选择' + asset.symbol" /></td
                  ><th
                    ><button class="screening-symbol" @click="openChart(asset.symbol)">{{
                      asset.symbol
                    }}</button
                    ><small>{{ asset.name }}</small
                    ><small
                      class="screening-reference-quote"
                      :title="'原生已完成日线 · ' + lastDate(asset.symbol, '1D')"
                      >{{ referenceQuote(asset.symbol) }}</small
                    ></th
                  ><td
                    >{{ assetClass(asset) }}<small>{{ asset.category }}</small
                    ><small>{{ capLabel(asset, caps) }}</small></td
                  ><td
                    ><button
                      v-if="sortEvent(asset.symbol)"
                      class="screening-event"
                      @click="
                        openChart(
                          asset.symbol,
                          sortEvent(asset.symbol)!.frame,
                          sortEvent(asset.symbol)!.t,
                        )
                      "
                      >{{ day(sortEvent(asset.symbol)!.t)
                      }}<small
                        >{{ FRAME_NAMES[sortEvent(asset.symbol)!.frame] }} ·
                        {{ directionLabel(sortEvent(asset.symbol)!.previous) }} →
                        {{ directionLabel(sortEvent(asset.symbol)!.direction) }}</small
                      ><small>{{ sortEvent(asset.symbol)!.age }}根前</small></button
                    ><span v-else>无符合条件的转向</span></td
                  ><td v-for="f in FRAMES" :key="f"
                    ><button
                      :class="['screening-direction', tone(stateFor(asset.symbol, f))]"
                      @click="openChart(asset.symbol, f)"
                      >{{ directionLabel(stateFor(asset.symbol, f)) }}</button
                    ><small>{{ lastDate(asset.symbol, f) }}</small
                    ><button
                      v-if="latestTransition(asset.symbol, f)"
                      class="screening-event"
                      @click="openChart(asset.symbol, f, latestTransition(asset.symbol, f)!.t)"
                      >{{ day(latestTransition(asset.symbol, f)!.t) }} 转{{
                        directionLabel(latestTransition(asset.symbol, f)!.direction)
                      }}</button
                    ><template v-if="matrixExpanded"
                      ><small v-for="system in SYSTEMS.filter((s) => s !== 'zlma')" :key="system"
                        >{{ SYSTEM_NAMES[system] }}：{{
                          directionLabel(
                            summaries.get(asset.symbol + '/' + f)?.assessed.current.systems[system]
                              .direction || '不足',
                          )
                        }}</small
                      ></template
                    ></td
                  ><td><button @click="profile = asset">档案</button></td></tr
                ><tr v-if="!pageRows.length"
                  ><td colspan="9" class="screening-empty"
                    >暂无符合条件的标的
                    <button v-if="activeFilters.length" @click="resetFilters"
                      >清除条件，查看全部</button
                    ><span v-else>可在数据与备份中检查行情覆盖。</span></td
                  ></tr
                ></tbody
              ></table
            ></div
          >
          <div class="screening-pagination"
            ><button :disabled="page <= 1" @click="page--">上一页</button
            ><span>{{ page }} / {{ Math.max(1, Math.ceil(rows.length / 25)) }}</span
            ><button :disabled="page * 25 >= rows.length" @click="page++">下一页</button></div
          >
        </template>
        <template v-else>
          <div class="screening-controls screening-card"
            ><label
              >信号体系<select aria-label="信号体系" v-model="eventSystem"
                ><option value="composite">零滞后主方向</option
                ><option
                  v-for="s in SYSTEMS.filter((value) => value !== 'zlma')"
                  :key="s"
                  :value="s"
                  >{{ SYSTEM_NAMES[s] }}</option
                ><option value="original">原始交叉 / 趋势位</option></select
              ></label
            ><label
              >信号周期<select aria-label="信号周期" v-model="eventFrame"
                ><option value="all">全部周期</option
                ><option v-for="f in FRAMES" :key="f" :value="f">{{
                  FRAME_NAMES[f]
                }}</option></select
              ></label
            ><label
              >信号方向<select aria-label="信号方向" v-model="eventSide"
                ><option value="all">全部方向</option
                ><option value="多">偏多</option
                ><option value="空">偏空</option
                ><option value="震荡">中性</option></select
              ></label
            ><span>{{ events.length }}条历史信号</span
            ><button @click="exportSignals">导出筛选信号JSON</button></div
          >
          <div class="screening-table" tabindex="0" role="region" aria-label="历史信号"
            ><table
              ><thead
                ><tr
                  ><th>观测K线起始日</th><th>标的</th><th>周期</th><th>状态变化</th
                  ><th>事件 / 判定依据</th><th>距今根数</th><th>图上标记日</th><th>确认状态</th></tr
                ></thead
              ><tbody
                ><tr
                  v-for="(event, index) in events.slice(0, eventLimit)"
                  :key="event.symbol + event.frame + event.t + index"
                  ><td
                    ><button @click="openChart(event.symbol, event.frame, event.t)">{{
                      day(event.t)
                    }}</button></td
                  ><th>{{ event.symbol }}</th
                  ><td>{{ FRAME_NAMES[event.frame] }}</td
                  ><td :class="tone(event.side)"
                    >{{ event.previous ? directionLabel(event.previous) + ' → ' : ''
                    }}{{ directionLabel(event.side) }}</td
                  ><td
                    >{{ event.kind }}<small>{{ event.reason }}</small></td
                  ><td>{{ event.age }}</td
                  ><td>{{ day(event.plottedAt) }}</td
                  ><td>{{ event.provisional ? '待收盘' : '保守确认' }}</td></tr
                ><tr v-if="!events.length"><td colspan="8">暂无符合条件的历史信号</td></tr></tbody
              ></table
            ></div
          ><button v-if="events.length > eventLimit" @click="eventLimit += 100"
            >加载更多（已显示{{ eventLimit }} / {{ events.length }}）</button
          >
          <p class="screening-muted"
            >信号按当时已完成K线计算；图上回画日期不代表提前可知。参考体系事件不改变零滞后主方向。</p
          >
        </template>
      </template>
      <section v-else-if="tab === 'rules'" class="screening-card screening-prose">
        <h3>主方向：零滞后趋势</h3
        ><p
          >零滞后线为 EMA15(2 × 收盘价 −
          EMA15)。主方向至少需要60根已完成K线；零滞后线与EMA15之差超过0.1 ×
          ATR20，且零滞后线最近3根斜率同向，连续2根满足后确认偏多或偏空。条件解除立即转中性；缺历史标为待验证。</p
        >
        <h3>四套趋势体系</h3
        ><p
          >蒲鲁：144/169、288/338、576/676三条EMA通道同向，EMA676初始化种子残余不高于1%。简单/指数均线：20、60、100、200，四项证据至少三项同向，并要求价格相对200均线及20线斜率同向；EMA200也需要充分预热。三套体系与Kalman均为辅助观察。</p
        >
        <h3>原生与滚动周期</h3
        ><p
          >矩阵和信号采用原生日、三日、周、月K线；未声明末根已完成时保守剔除末根。图表可使用同源日线按交易日历聚合的滚动高周期，未完成周期明确标为预览；历史信号定位始终使用原生周期。日线缺口不补零。内置日历未来节假日配置覆盖2026—2028，超范围的滚动覆盖不可视为已核验。</p
        >
        <h3>辅助指标与资产语义</h3
        ><p
          >MACD采用12/26/9，柱值为DIF减DEA；RSI采用14期。成交额仅为周期收盘价乘成交量的估算。债券价格偏多通常对应收益率下行；派息、杠杆每日重置和期货展期未包含在价格方向内。</p
        >
        <ul
          ><li v-for="asset in assets" :key="asset.symbol"
            ><strong>{{ asset.symbol }}</strong
            >：{{ assetPolicy(asset).note }}</li
          ></ul
        >
        <h3>规则与研究档案</h3
        ><p>当前规则没有匹配的回测报告，不能用下列旧规则回测评价当前方向或选参。</p
        ><details
          ><summary>旧版回测归档 · 非当前规则</summary
          ><p
            >{{ archiveInfo.legacyResearch.rulesVersion }} ·
            {{ archiveInfo.legacyResearch.generatedAt }}</p
          ><button @click="download('旧版研究归档-非当前规则.json', archiveInfo!.legacyResearch)"
            >导出旧版研究原始记录</button
          ><div class="screening-table"
            ><table
              ><thead
                ><tr
                  ><th>标的 / 体系</th><th>训练收益</th><th>留出收益</th><th>留出最大回撤</th></tr
                ></thead
              ><tbody
                ><tr v-for="(r, i) in archiveInfo.legacyResearch.rows" :key="i"
                  ><th>{{ r.symbol }} / {{ r.system }}</th
                  ><td>{{ percent(r.train.return) }}</td
                  ><td>{{ percent(r.test.return) }}</td
                  ><td>{{ percent(r.test.maxDrawdown) }}</td></tr
                ></tbody
              ></table
            ></div
          ></details
        >
      </section>
      <section v-else-if="tab === 'quality'" class="screening-card">
        <h3>原生周期覆盖</h3
        ><p class="screening-muted"
          >有效根数按保守收盘规则计算。待验证只影响对应体系，其他体系继续独立显示。</p
        ><div class="screening-controls"
          ><label
            >周期<select aria-label="数据质量周期" v-model="qualityFrame"
              ><option value="all">全部周期</option
              ><option v-for="f in FRAMES" :key="f" :value="f">{{ FRAME_NAMES[f] }}</option></select
            ></label
          ><button @click="exportCoverage">导出覆盖记录</button></div
        >
        <div class="screening-table" tabindex="0" role="region" aria-label="行情数据覆盖"
          ><table
            ><thead
              ><tr
                ><th>标的</th><th>周期</th><th>有效 / 原始根数</th><th>有效日期范围</th
                ><th>主方向 / PMA / SMA / EMA</th><th>末根</th><th>来源 / 采集时间</th></tr
              ></thead
            ><tbody
              ><tr v-for="entry in coverage" :key="entry.symbol + entry.frame"
                ><th>{{ entry.symbol }}</th
                ><td>{{ FRAME_NAMES[entry.frame] }}</td
                ><td>{{ entry.valid }} / {{ entry.total }}</td
                ><td>{{ entry.first }} — {{ entry.last }}</td
                ><td>{{ entry.states.join(' / ') }}</td
                ><td>{{ entry.complete ? '已确认完成' : '未确认，已剔除' }}</td
                ><td
                  >{{ entry.source }}<small>{{ timestamp(entry.fetchedAt) }}</small
                  ><details
                    ><summary>来源证据</summary><p>{{ entry.evidence || '未附额外证据' }}</p
                    ><code>{{ entry.hash }}</code
                    ><p>{{ entry.issues.join('；') || '无记录的问题' }}</p></details
                  ></td
                ></tr
              ></tbody
            ></table
          ></div
        >
      </section>
      <section v-else-if="tab === 'data'" class="screening-card screening-prose">
        <h3>行情、市值与完整备份</h3
        ><p
          >当前数据{{
            imported ? '来自本浏览器导入' : '来自分享包历史归档'
          }}。导入只保存在当前浏览器并按账号区分，文件不会上传。原生行情需提供秒时间戳 t、开高低收
          o/h/l/c、成交量 v；缺失周期保留缺失。</p
        ><div class="screening-controls"
          ><button @click="chooseImport('snapshot')">导入行情JSON</button
          ><button @click="download('跨资产行情快照.json', archive)">导出行情与格式</button
          ><button @click="chooseImport('caps')">导入市值JSON</button
          ><button @click="download('跨资产市值快照.json', caps)">导出市值与格式</button
          ><button @click="exportBackup">导出完整备份</button
          ><button @click="chooseImport('backup')">导入完整备份</button
          ><button :disabled="busy" @click="restoreArchive">恢复平台归档行情</button></div
        >
        <p
          >完整备份包含行情、市值、自选清单与偏好；支持原分享包的完整备份。恢复归档行情会保留自选与筛选条件。</p
        ><details
          ><summary>操作说明</summary
          ><ol
            ><li
              >在趋势矩阵组合搜索、资产范围、行业、市值与周期条件；“本轮转向仍有效”只保留持续至今的那次转向。</li
            ><li
              >点击周期方向打开K线，点击转向日期或信号观测日定位历史；支持四周期同屏、拖动和缩放。</li
            ><li>创建自选后，勾选标的加入清单；筛选变化保留勾选，可批量加入当前结果。</li
            ><li
              >更新行情请导入同格式原生周期快照；导入前完整校验，失败保留现有数据。没有连接在线行情采集服务。</li
            ><li>浏览器清理数据或更换设备前导出完整备份。</li></ol
          ></details
        >
      </section>
    </template>
    <input
      ref="fileInput"
      hidden
      type="file"
      accept=".json,application/json"
      @change="importFile"
    />
    <Modal
      :open="chartOpen"
      :title="selectedAsset ? selectedAsset.symbol + ' · ' + selectedAsset.name : '多周期趋势'"
      :footer="null"
      width="min(1440px, calc(100vw - 32px))"
      centered
      wrap-class-name="cross-asset-chart-modal"
      :destroy-on-close="true"
      @cancel="closeChart"
    >
      <div v-if="selectedAsset" class="cross-asset-screening screening-chart-workspace">
        <div class="screening-chart-toolbar">
          <div class="screening-controls screening-chart-main-controls"
            ><button :disabled="!cycleAssets.length" @click="stepAsset(-1)">上一标的</button
            ><label
              >图表标的<select
                aria-label="图表标的"
                :value="symbol"
                @change="openChart(($event.target as HTMLSelectElement).value, frame)"
                ><option
                  v-if="selectedAsset && !pickerAssets.some((asset) => asset.symbol === symbol)"
                  :value="symbol"
                  >{{ selectedAsset.symbol }} · {{ selectedAsset.name }}（当前）</option
                ><option v-for="asset in pickerAssets" :key="asset.symbol" :value="asset.symbol"
                  >{{ asset.symbol }} · {{ asset.name }}</option
                ></select
              ></label
            ><button :disabled="!cycleAssets.length" @click="stepAsset(1)">下一标的</button
            ><label
              >周期<select
                aria-label="图表周期"
                :value="frame"
                @change="openChart(symbol, ($event.target as HTMLSelectElement).value as Frame)"
                ><option v-for="f in FRAMES" :key="f" :value="f">{{
                  FRAME_NAMES[f]
                }}</option></select
              ></label
            ><label
              >显示根数<select aria-label="显示根数" v-model.number="range"
                ><option :value="60">60</option
                ><option :value="120">120</option
                ><option :value="250">250</option
                ><option :value="0">全部</option></select
              ></label
            ><label><input v-model="gridCharts" type="checkbox" />四周期同屏</label
            ><label
              ><input v-model="rolling" type="checkbox" :disabled="!!signalAt" />滚动高周期</label
            ><label
              ><input
                v-model="levels"
                type="checkbox"
                :disabled="!groups.includes('zlma')"
              />趋势位与事件</label
            ><a :href="tvLink(selectedAsset, frame)" target="_blank" rel="noopener noreferrer"
              >TradingView ↗</a
            ></div
          >
          <div class="screening-controls screening-chart-picker-controls"
            ><label
              >图表搜索<input
                v-model="chartQuery"
                aria-label="图表标的搜索"
                placeholder="代码 / 名称" /></label
            ><label
              >图表资产大类<select v-model="chartCategory" aria-label="图表资产大类"
                ><option value="all">全部大类</option
                ><option v-for="category in chartCategories" :key="category" :value="category">{{
                  category
                }}</option></select
              ></label
            ><span v-if="!pickerAssets.length">暂无匹配标的</span></div
          >
          <div class="screening-controls screening-chart-overlay-controls"
            ><label v-for="s in SYSTEMS" :key="s"
              ><input v-model="groups" type="checkbox" :value="s" />{{ SYSTEM_NAMES[s] }}</label
            ><label v-for="a in AUXILIARIES" :key="a"
              ><input v-model="auxiliary" type="checkbox" :value="a" />{{
                AUXILIARY_NAMES[a]
              }}</label
            ><label v-for="k in KALMAN_OVERLAYS" :key="k"
              ><input v-model="kalman" type="checkbox" :value="k" />{{ KALMAN_NAMES[k] }}</label
            ><label
              >蜡烛染色<select
                aria-label="蜡烛染色"
                v-model="kalmanPaint"
                :disabled="!kalman.length"
                ><option value="none">不染色</option
                ><option v-for="k in kalman" :key="k" :value="k">{{
                  KALMAN_NAMES[k]
                }}</option></select
              ></label
            ></div
          >
          <div
            class="screening-controls screening-chart-direction-controls"
            aria-label="四周期原生确认方向"
            ><button
              v-for="f in FRAMES"
              :key="f"
              :aria-pressed="frame === f"
              @click="openChart(symbol, f)"
              >{{ FRAME_NAMES[f] }} · {{ directionLabel(stateFor(symbol, f)) }}</button
            ><label
              >加入清单<select v-model="chartList" aria-label="图表加入自选清单"
                ><option v-for="list in watchlists" :key="list.id" :value="list.id">{{
                  list.name
                }}</option></select
              ></label
            ><button :disabled="!chartList" @click="addMembers([symbol], chartList)"
              >加入当前标的</button
            ></div
          >
        </div>
        <p v-if="signalAt" class="screening-source"
          >历史信号观测日 {{ day(signalAt) }} · 原生周期（K线起始日，收盘后确认）
          <span v-if="gridCharts"
            >仅定位{{ FRAME_NAMES[frame] }}，其余周期展示各自最新已完成历史。</span
          ><button @click="returnToLatest">回到最新</button></p
        >
        <div :class="{ 'screening-chart-grid': gridCharts }"
          ><article v-for="f in chartFrames" :key="symbol + f"
            ><ChartExpand
              v-slot="{ expanded }"
              class="screening-chart-expand"
              :title="`${selectedAsset.symbol} · ${selectedAsset.name} · ${FRAME_NAMES[f]}`"
              ><h3
                >{{ FRAME_NAMES[f] }} ·
                {{
                  chartSource(f)?.rolling
                    ? chartSource(f)?.lastBarComplete
                      ? '日线滚动聚合 · 已完成周期'
                      : '日线滚动聚合 · 含未完成周期预览'
                    : '原生周期 · 已完成K线'
                }}</h3
              ><p v-if="chartSource(f)?.rolling" class="screening-muted"
                >日线截至 {{ chartSource(f)?.rolling?.dailyAsOf }} · 当前桶截至
                {{ chartSource(f)?.rolling?.asOf }} · 缺失桶 {{ chartSource(f)?.rolling?.missing
                }}{{ chartSource(f)?.rolling?.currentGap ? ' · 当前周期有日线缺口' : '' }}</p
              ><TrendChart
                v-if="chartSource(f)"
                :source="chartSource(f)!"
                :frame="f"
                :expanded="expanded"
                :groups="groups"
                :auxiliary="auxiliary"
                :kalman="kalman"
                :kalman-paint="kalman.includes(kalmanPaint as KalmanOverlay) ? kalmanPaint : 'none'"
                :range="range"
                :levels="levels && groups.includes('zlma')"
                :signal-at="f === frame ? signalAt : undefined"
              /><p v-else>暂无该周期行情</p></ChartExpand
            ><TrendEvidence
              v-if="chartSource(f)"
              :source="chartSource(f)!"
              :groups="groups"
              :signal-at="f === frame ? signalAt : undefined" /></article
        ></div>
        <p class="screening-muted">{{ assetPolicy(selectedAsset).note }}</p>
      </div>
    </Modal>
    <Modal
      :open="!!profile"
      :title="profile?.symbol + ' · 标的研究档案'"
      :footer="null"
      width="min(720px, calc(100vw - 32px))"
      centered
      wrap-class-name="cross-asset-profile-modal"
      @cancel="profile = undefined"
      ><div v-if="profile" class="screening-prose"
        ><h3>{{ profile.name }}</h3
        ><p>{{ profile.english }}</p
        ><p>{{ profile.category }} / {{ profile.sector }}</p
        ><p>{{ profile.profile || profile.reason }}</p
        ><h4>主要驱动</h4><p>{{ profile.drivers || '未提供' }}</p
        ><h4>风险因素</h4><p>{{ profile.risks || '未提供' }}</p
        ><p class="screening-muted">研究快照 {{ archiveInfo?.sourceDate }}，未实时刷新</p
        ><button
          @click="
            openChart(profile!.symbol);
            profile = undefined;
          "
          >查看四周期趋势</button
        ></div
      ></Modal
    >
  </section>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
  import { Modal } from 'ant-design-vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import {
    getCrossAssetScreening,
    readScreeningData,
    persistScreeningData,
    validateSnapshot,
    validateCaps,
    validateBackup,
    validateWatchlists,
    type ScreeningArchive,
    type Watchlist,
  } from '@/api/platform/crossAssetScreening';
  import {
    FRAMES,
    FRAME_NAMES,
    type Snapshot,
    type SnapshotSeries,
    type Frame,
    type Direction,
  } from './crossAsset/engine';
  import { type Security } from './crossAsset/model';
  import {
    assetClass,
    assetPolicy,
    directionLabel,
    DEFAULT_RULE,
    RULE_VERSION,
    SYSTEMS,
    SYSTEM_NAMES,
    type System,
  } from './crossAsset/rules';
  import {
    defaultTrendFilters,
    defaultTrendSort,
    matchesTrend,
    sortTransition,
    compareEventTime,
    frameTransitions,
    hasTurnCondition,
    readFilterSettings,
    TREND_PRESETS,
    type AssetTrends,
    type TrendFilters as Filters,
    type TrendSort,
    type TrendPreset,
  } from './crossAsset/filters';
  import {
    defaultAssetScreen,
    matchesAssetScreen,
    effectiveAssetScreen,
    capRangeError,
    capLabel,
    type CapSnapshot,
    type AssetScreen,
  } from './crossAsset/assetScreen';
  import { summarizeSeries } from './crossAsset/summary';
  import { rollingMonitorSeries } from './crossAsset/rolling.mjs';
  import { AUXILIARIES, AUXILIARY_NAMES, type Auxiliary } from './crossAsset/auxiliary';
  import { KALMAN_OVERLAYS, KALMAN_NAMES, type KalmanOverlay } from './crossAsset/kalman';
  import TrendFilters from './crossAsset/TrendFilters.vue';
  import ChartExpand from '../components/ChartExpand.vue';
  import TrendChart from './crossAsset/TrendChart.vue';
  import TrendEvidence from './crossAsset/TrendEvidence.vue';
  import WorkbookScreener from './crossAsset/WorkbookScreener.vue';

  const user = useUserStore(),
    route = useRoute(),
    router = useRouter();
  const account = String(user.getUserInfo.userId || 'anonymous');
  const settingsKey = `vg:cross-asset-screening:v1:${account}`;
  function saved(): Record<string, any> {
    try {
      const value = JSON.parse(localStorage.getItem(settingsKey) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch {
      return {};
    }
  }
  const initial = saved(),
    settings = readFilterSettings(initial);
  const query = ref(typeof initial.query === 'string' ? initial.query : ''),
    kind = ref(initial.kind || 'all'),
    scope = ref(initial.scope || 'all'),
    structure = ref(initial.structure || 'all');
  const trendFilters = ref(settings?.filters || defaultTrendFilters()),
    sort = ref(settings?.sort || defaultTrendSort());
  function normalizeAsset(value: unknown): AssetScreen {
    const v = value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
    const strings = (name: string) =>
      Array.isArray(v[name])
        ? (v[name] as unknown[]).filter((s): s is string => typeof s === 'string')
        : [];
    const unit = typeof v.unit === 'number' && [1, 1e8, 1e9, 1e12].includes(v.unit) ? v.unit : 1e8;
    const bound = (value: unknown) =>
      typeof value === 'string'
        ? value === '' || !Number.isFinite(Number(value))
          ? value
          : String((Number(value) * unit) / 1e8)
        : '';
    return {
      ...defaultAssetScreen(),
      sectors: strings('sectors'),
      industries: strings('industries'),
      etfs: strings('etfs'),
      min: bound(v.min),
      max: bound(v.max),
      unit: 1e8,
      includeUnknown: v.includeUnknown === true,
      includeStale: v.includeStale === true,
      keepEtfs: v.keepEtfs === true,
    };
  }
  const assetScreen = ref(normalizeAsset(initial.assetScreen));
  const presets = ref<TrendPreset[]>(
    Array.isArray(initial.presets)
      ? initial.presets
          .filter(
            (p) =>
              p &&
              typeof p.id === 'string' &&
              typeof p.name === 'string' &&
              p.name.length <= 40 &&
              readFilterSettings(p),
          )
          .slice(0, 30)
      : [],
  );
  const watchlists = ref<Watchlist[]>([]),
    activeWatchlist = ref(''),
    picked = ref<string[]>([]),
    listName = ref('');
  const chosenPreset = ref(''),
    presetRename = ref(''),
    matrixExpanded = ref(false);
  const holdingSymbols = ref<string[]>(
    Array.isArray(initial.holdingSymbols)
      ? initial.holdingSymbols.filter((s) => typeof s === 'string')
      : [],
  );
  const archiveInfo = shallowRef<ScreeningArchive>(),
    archive = shallowRef<Snapshot>(),
    caps = shallowRef<CapSnapshot | null>(null),
    imported = ref(false);
  const loading = ref(false),
    busy = ref(false),
    error = ref(''),
    notice = ref(''),
    tab = ref('matrix'),
    page = ref(1),
    eventLimit = ref(100);
  const eventSystem = ref('composite'),
    eventFrame = ref('all'),
    eventSide = ref('all'),
    qualityFrame = ref('all');
  const hasWorkbook = computed(() =>
    Boolean(archiveInfo.value?.workbookSnapshot || archiveInfo.value?.workbookSnapshotUnavailable),
  );
  const tabs = computed(() => [
    ...(hasWorkbook.value ? [{ key: 'workbook', label: '标的筛选' }] : []),
    { key: 'matrix', label: '趋势矩阵' },
    { key: 'signals', label: '信号历史' },
    { key: 'rules', label: '规则与研究' },
    { key: 'quality', label: '数据质量' },
    { key: 'data', label: '数据与备份' },
  ]);
  const assets = computed(() => archiveInfo.value?.assets || []);
  const symbols = computed(() => assets.value.map((s) => s.symbol));
  const stocks = computed(() =>
    assets.value.filter((s) => s.kind === 'stock').map((s) => s.symbol),
  );
  const sectors = computed(() => [
    ...new Set(assets.value.filter((s) => s.kind === 'stock').map((s) => s.sector)),
  ]);
  const industries = computed(() => [
    ...new Set(assets.value.filter((s) => s.kind === 'stock').map((s) => s.category)),
  ]);
  const etfCategories = computed(() => [
    ...new Set(assets.value.filter((s) => s.kind === 'etf').map((s) => s.category)),
  ]);
  const summaries = computed(
    () =>
      new Map(
        (archive.value?.series || []).map((s) => [
          `${s.symbol}/${s.frame}`,
          summarizeSeries(s, false, DEFAULT_RULE),
        ]),
      ),
  );
  const trends = computed(() => {
    const out = new Map<string, AssetTrends>();
    for (const summary of summaries.value.values()) {
      const s = summary.source,
        item = out.get(s.symbol) || {};
      item[s.frame] = summary.trend;
      out.set(s.symbol, item);
    }
    return out;
  });
  const stateFor = (s: string, f: Frame): Direction => trends.value.get(s)?.[f]?.current || '不足';
  const latestTransition = (s: string, f: Frame) => trends.value.get(s)?.[f]?.events.at(-1);
  const sortEvent = (s: string) =>
    sortTransition(trends.value.get(s) || {}, trendFilters.value, sort.value);
  function flags(s: string) {
    const values = FRAMES.map((f) => stateFor(s, f));
    return {
      bull: values.every((d) => d === '多'),
      bear: values.every((d) => d === '空'),
      conflict: values.includes('多') && values.includes('空'),
      short: values.includes('不足'),
    };
  }
  const counts = computed(() =>
    assets.value.reduce(
      (out, s) => {
        const f = flags(s.symbol);
        for (const key of ['bull', 'bear', 'conflict', 'short'] as const)
          out[key] += Number(f[key]);
        return out;
      },
      { bull: 0, bear: 0, conflict: 0, short: 0 },
    ),
  );
  const structureOptions = [
    { key: 'bull', label: '四周期偏多' },
    { key: 'bear', label: '四周期偏空' },
    { key: 'conflict', label: '周期分歧' },
    { key: 'short', label: '历史待验证' },
  ];
  function toggleStructure(value: string) {
    structure.value = structure.value === value ? 'all' : value;
    tab.value = 'matrix';
  }
  const activeFilters = computed(() => {
    const items: Array<{ key: string; label: string; clear: () => void }> = [];
    if (query.value.trim())
      items.push({
        key: 'query',
        label: '搜索：' + query.value.trim(),
        clear: () => {
          query.value = '';
        },
      });
    if (kind.value !== 'all')
      items.push({
        key: 'kind',
        label: kind.value === 'stock' ? '个股' : 'ETF',
        clear: () => {
          kind.value = 'all';
        },
      });
    if (scope.value !== 'all')
      items.push({
        key: 'scope',
        label:
          {
            covered: '已覆盖',
            holdings: '备份持仓',
            sp500: '标普500',
            ndx: '纳斯达克100',
            curated: '精选个股',
          }[scope.value] || '范围',
        clear: () => {
          scope.value = 'all';
        },
      });
    if (structure.value !== 'all')
      items.push({
        key: 'structure',
        label: structureOptions.find((item) => item.key === structure.value)?.label || '结构',
        clear: () => {
          structure.value = 'all';
        },
      });
    const list = watchlists.value.find((item) => item.id === activeWatchlist.value);
    if (list)
      items.push({
        key: 'watchlist',
        label: '自选：' + list.name,
        clear: () => {
          activeWatchlist.value = '';
        },
      });
    if (JSON.stringify(assetScreen.value) !== JSON.stringify(defaultAssetScreen()))
      items.push({
        key: 'asset',
        label: '行业 / 市值条件',
        clear: () => {
          assetScreen.value = defaultAssetScreen();
        },
      });
    if (JSON.stringify(trendFilters.value) !== JSON.stringify(defaultTrendFilters()))
      items.push({
        key: 'trend',
        label: '周期组合条件',
        clear: () => {
          changeTrend(defaultTrendFilters(), sort.value);
        },
      });
    return items;
  });
  function referenceQuote(value: string) {
    const bars = summaries.value.get(value + '/1D')?.computed.bars || [],
      last = bars.at(-1),
      previous = bars.at(-2);
    if (!last) return '暂无参考收盘';
    const change = previous && previous.c > 0 ? (last.c / previous.c - 1) * 100 : null;
    return (
      '参考收盘 $' +
      last.c.toFixed(2) +
      (change === null ? '' : ' · ' + (change > 0 ? '+' : '') + change.toFixed(2) + '%')
    );
  }
  const rows = computed(() => {
    const list = watchlists.value.find((w) => w.id === activeWatchlist.value);
    const result = assets.value.filter(
      (s) =>
        (!list || list.symbols.includes(s.symbol)) &&
        (kind.value === 'all' || kind.value === s.kind) &&
        (scope.value === 'all' ||
          (scope.value === 'covered' && trends.value.has(s.symbol)) ||
          (scope.value === 'holdings' && holdingSymbols.value.includes(s.symbol)) ||
          s[scope.value] === true) &&
        `${s.symbol} ${s.name} ${s.english} ${s.category}`
          .toLowerCase()
          .includes(query.value.toLowerCase().trim()) &&
        (structure.value === 'all' || flags(s.symbol)[structure.value]) &&
        matchesAssetScreen(s, effectiveAssetScreen(assetScreen.value, kind.value), caps.value) &&
        matchesTrend(trends.value.get(s.symbol) || {}, trendFilters.value),
    );
    const event = (s: Security) =>
      sortTransition(trends.value.get(s.symbol) || {}, trendFilters.value, sort.value)?.t;
    return result.sort(
      (a, b) =>
        (sort.value.by === 'symbol'
          ? a.symbol.localeCompare(b.symbol) * (sort.value.order === 'asc' ? 1 : -1)
          : sort.value.by === 'event'
          ? compareEventTime(event(a), event(b), sort.value.order)
          : (Number(flags(b.symbol).conflict) * 3 +
              Number(flags(b.symbol).bull || flags(b.symbol).bear) * 2 -
              Number(flags(a.symbol).conflict) * 3 -
              Number(flags(a.symbol).bull || flags(a.symbol).bear) * 2) *
            (sort.value.order === 'desc' ? 1 : -1)) || a.symbol.localeCompare(b.symbol),
    );
  });
  const pageRows = computed(() => rows.value.slice((page.value - 1) * 25, page.value * 25));
  const events = computed(() => {
    const selected = new Set(rows.value.map((s) => s.symbol)),
      turn = hasTurnCondition(trendFilters.value);
    return [...summaries.value.values()]
      .flatMap((v) => {
        const s = v.source,
          r = trendFilters.value.rules[s.frame];
        if (
          !selected.has(s.symbol) ||
          (eventFrame.value !== 'all' && eventFrame.value !== s.frame) ||
          (turn && r.turn === 'any')
        )
          return [];
        if (turn && r.state !== 'any' && r.state !== v.trend.current) return [];
        const allowed = new Set(
          frameTransitions(v.trend, r, trendFilters.value.stillCurrent).map(
            (e) => `${e.t}/${e.direction}`,
          ),
        );
        if (turn && !allowed.size) return [];
        return v.events.filter(
          (e) =>
            e.system === eventSystem.value &&
            (eventSide.value === 'all' || e.side === eventSide.value) &&
            (!turn ||
              (e.system === 'composite'
                ? allowed.has(`${e.t}/${e.side}`)
                : r.lookback === 0 || e.age < r.lookback)),
        );
      })
      .sort((a, b) => b.t - a.t || a.symbol.localeCompare(b.symbol));
  });
  const day = (t: number) => new Date(t * 1000).toISOString().slice(0, 10);
  const timestamp = (v: string) =>
    Number.isFinite(Date.parse(v))
      ? new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) +
        ' 北京时间'
      : '—';
  const tone = (d: Direction) =>
    d === '多' ? 'is-bull' : d === '空' ? 'is-bear' : d === '不足' ? 'is-short' : 'is-neutral';
  const percent = (n: number) => (Number.isFinite(n) ? (n * 100).toFixed(2) + '%' : '—');
  const lastDate = (s: string, f: Frame) => {
    const b = summaries.value.get(`${s}/${f}`)?.computed.bars.at(-1);
    return b ? day(b.t) : '暂无数据';
  };
  const coverage = computed(() =>
    assets.value.flatMap((s) =>
      FRAMES.filter((f) => qualityFrame.value === 'all' || qualityFrame.value === f).map((f) => {
        const summary = summaries.value.get(`${s.symbol}/${f}`),
          source = archive.value?.series.find((v) => v.symbol === s.symbol && v.frame === f);
        return {
          symbol: s.symbol,
          frame: f,
          total: source?.bars.length || 0,
          valid: source ? source.bars.length - (source.lastBarComplete === true ? 0 : 1) : 0,
          first: source?.bars[0] ? day(source.bars[0].t) : '—',
          last: lastDate(s.symbol, f),
          complete: source?.lastBarComplete === true,
          states: (['zlma', 'pma', 'sma', 'ema'] as const).map((k) =>
            directionLabel(summary?.assessed.current.systems[k].direction || '不足'),
          ),
          source:
            source?.source ||
            (source
              ? imported.value
                ? '本地导入 · 未声明行情来源'
                : '分享包原生周期归档'
              : '未覆盖'),
          fetchedAt: source?.fetchedAt || '',
          hash: source?.hash || '',
          evidence: source?.evidence || '',
          issues: source?.issues || [],
        };
      }),
    ),
  );

  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    controller = new AbortController();
    const request = controller;
    loading.value = true;
    error.value = '';
    try {
      const info = await getCrossAssetScreening(request.signal);
      if (request.signal.aborted) return;
      let stored: Awaited<ReturnType<typeof readScreeningData>>;
      try {
        stored = await readScreeningData(account);
      } catch {
        notice.value = '浏览器行情存储不可用，当前读取平台归档；可导出备份保存修改。';
      }
      if (request.signal.aborted) return;
      let next = info.snapshot,
        nextCaps = info.caps;
      try {
        if (stored) {
          next = validateSnapshot(
            stored.snapshot,
            info.assets.map((s) => s.symbol),
          );
          nextCaps = validateCaps(
            stored.caps,
            info.assets.filter((s) => s.kind === 'stock').map((s) => s.symbol),
          );
        }
      } catch {
        next = info.snapshot;
        nextCaps = info.caps;
        notice.value =
          '已保存的本地行情格式无效，当前显示平台归档；可在数据与备份重新导入或恢复归档。';
      }
      const firstLoad = !archiveInfo.value;
      archiveInfo.value = info;
      if (firstLoad && hasWorkbook.value && !route.query.symbol) tab.value = 'workbook';
      if (tab.value === 'workbook' && !hasWorkbook.value) tab.value = 'matrix';
      if (!symbols.value.includes(symbol.value)) symbol.value = symbols.value[0] || 'AAPL';
      archive.value = next;
      caps.value = nextCaps;
      imported.value = JSON.stringify(next) !== JSON.stringify(info.snapshot);
      try {
        watchlists.value = validateWatchlists(
          saved().watchlists || [
            {
              id: 'favorites',
              name: '默认自选',
              symbols: ['AAPL', 'NVDA', 'SPY', 'QQQ', 'GLD', 'TLT'].filter((s) =>
                symbols.value.includes(s),
              ),
            },
          ],
          symbols.value,
        );
      } catch {
        watchlists.value = [];
        notice.value = '已保存自选格式无效，请导入完整备份恢复。';
      }
      activeWatchlist.value = watchlists.value.some((w) => w.id === saved().activeWatchlist)
        ? saved().activeWatchlist
        : '';
      followRoute();
    } catch (e) {
      if (!request.signal.aborted)
        error.value = '跨资产数据读取失败：' + (e instanceof Error ? e.message : String(e));
    } finally {
      if (!request.signal.aborted) loading.value = false;
    }
  }
  function settingsValue() {
    return {
      query: query.value,
      kind: kind.value,
      scope: scope.value,
      holdingSymbols: holdingSymbols.value,
      structure: structure.value,
      filters: trendFilters.value,
      sort: sort.value,
      assetScreen: assetScreen.value,
      presets: presets.value,
      watchlists: watchlists.value,
      activeWatchlist: activeWatchlist.value,
      chart: {
        symbol: symbol.value,
        frame: frame.value,
        range: range.value,
        groups: groups.value,
        auxiliary: auxiliary.value,
        kalman: kalman.value,
        kalmanPaint: kalmanPaint.value,
        rolling: rolling.value,
        gridCharts: gridCharts.value,
        levels: levels.value,
      },
    };
  }
  function storeSettings() {
    if (!archiveInfo.value) return;
    try {
      localStorage.setItem(settingsKey, JSON.stringify(settingsValue()));
    } catch {
      notice.value = '浏览器未允许保存偏好和自选，请导出完整备份。';
    }
  }
  function changeTrend(filters: Filters, value: TrendSort) {
    if (JSON.stringify(filters) !== JSON.stringify(trendFilters.value)) {
      eventSystem.value = 'composite';
      eventFrame.value = 'all';
      eventSide.value = 'all';
    }
    trendFilters.value = filters;
    sort.value = value;
  }
  function clearTrend() {
    changeTrend(defaultTrendFilters(), defaultTrendSort());
    structure.value = 'all';
  }
  function resetFilters() {
    query.value = '';
    kind.value = 'all';
    scope.value = 'all';
    activeWatchlist.value = '';
    assetScreen.value = defaultAssetScreen();
    clearTrend();
    eventFrame.value = 'all';
    eventSide.value = 'all';
    eventSystem.value = 'composite';
  }
  function applyPreset(p: TrendPreset) {
    changeTrend(JSON.parse(JSON.stringify(p.filters)), { ...p.sort });
    structure.value = 'all';
  }
  function savePreset(name: string) {
    const existing = presets.value.find((p) => p.name === name);
    if (existing) {
      notice.value = '已有同名方案；请选择该方案后使用“用当前条件更新方案”，或更换名称另存。';
    } else if (presets.value.length < 30)
      presets.value.push({
        id: crypto.randomUUID(),
        name,
        filters: JSON.parse(JSON.stringify(trendFilters.value)),
        sort: { ...sort.value },
      });
    else notice.value = '最多保存30个条件方案。';
  }
  function useChosenPreset() {
    const preset = presets.value.find((p) => p.id === chosenPreset.value);
    if (preset) {
      presetRename.value = preset.name;
      applyPreset(preset);
    }
  }
  function renamePreset() {
    const preset = presets.value.find((p) => p.id === chosenPreset.value),
      name = presetRename.value.trim();
    if (!preset || !name || name.length > 40) {
      notice.value = '方案名称需为1—40字。';
      return;
    }
    if (presets.value.some((p) => p.id !== preset.id && p.name === name)) {
      notice.value = '已有同名方案，请更换名称。';
      return;
    }
    preset.name = name;
  }
  function updatePreset() {
    const preset = presets.value.find((p) => p.id === chosenPreset.value);
    if (preset) {
      preset.filters = JSON.parse(JSON.stringify(trendFilters.value));
      preset.sort = { ...sort.value };
      notice.value = '已更新方案：' + preset.name;
    }
  }
  function removePreset(id: string) {
    presets.value = presets.value.filter((p) => p.id !== id);
    if (chosenPreset.value === id) chosenPreset.value = '';
  }
  function validListName() {
    const name = listName.value.trim();
    if (
      !name ||
      name.length > 40 ||
      watchlists.value.some(
        (w) => w.id !== activeWatchlist.value && w.name.toLowerCase() === name.toLowerCase(),
      )
    )
      throw Error('清单名称需为1—40字且不能重复。');
    return name;
  }
  function createList() {
    try {
      const name = validListName();
      if (watchlists.value.some((w) => w.name.toLowerCase() === name.toLowerCase()))
        throw Error('已有同名清单。');
      if (watchlists.value.filter((list) => list.id !== 'favorites').length >= 100)
        throw Error('最多创建100个自定义清单。');
      const list = { id: crypto.randomUUID(), name, symbols: [] };
      watchlists.value.push(list);
      activeWatchlist.value = list.id;
      listName.value = '';
    } catch (e) {
      notice.value = (e as Error).message;
    }
  }
  function renameList() {
    try {
      const list = watchlists.value.find((w) => w.id === activeWatchlist.value);
      if (list) list.name = validListName();
      listName.value = '';
    } catch (e) {
      notice.value = (e as Error).message;
    }
  }
  function deleteList() {
    if (activeWatchlist.value === 'favorites') return;
    watchlists.value = watchlists.value.filter((w) => w.id !== activeWatchlist.value);
    activeWatchlist.value = '';
  }
  function addMembers(values: string[], id = activeWatchlist.value) {
    const list = watchlists.value.find((w) => w.id === id);
    if (list) list.symbols = [...new Set([...list.symbols, ...values])];
  }
  const addPicked = () => addMembers(picked.value),
    addAll = () => addMembers(rows.value.map((s) => s.symbol));
  function removePicked() {
    const list = watchlists.value.find((w) => w.id === activeWatchlist.value);
    if (list) list.symbols = list.symbols.filter((s) => !picked.value.includes(s));
  }
  function pickPage(event: Event) {
    const current = pageRows.value.map((s) => s.symbol);
    picked.value = (event.target as HTMLInputElement).checked
      ? [...new Set([...picked.value, ...current])]
      : picked.value.filter((s) => !current.includes(s));
  }
  function download(name: string, data: unknown) {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  function exportSignals() {
    download('跨资产当前筛选历史信号.json', {
      generatedAt: archive.value?.generatedAt,
      exportedAt: new Date().toISOString(),
      rulesVersion: RULE_VERSION,
      config: DEFAULT_RULE,
      mode: 'conservative-closed',
      pineParity: 'pending',
      exportScope: 'filtered',
      total: events.value.length,
      filters: {
        ...settingsValue(),
        eventSystem: eventSystem.value,
        eventFrame: eventFrame.value,
        eventSide: eventSide.value,
      },
      sources: archive.value?.series.map((s) => ({
        symbol: s.symbol,
        frame: s.frame,
        hash: s.hash,
        source: s.source,
        fetchedAt: s.fetchedAt,
      })),
      events: events.value,
    });
    notice.value = `已导出全部${events.value.length}条筛选信号。`;
  }
  const exportCoverage = () =>
    download('跨资产行情覆盖.json', {
      generatedAt: archive.value?.generatedAt,
      rows: coverage.value,
    });
  const exportBackup = () =>
    download('跨资产筛选完整备份.json', {
      format: 'global-variable-cross-asset',
      version: 1,
      exportedAt: new Date().toISOString(),
      snapshot: archive.value,
      caps: caps.value,
      watchlists: watchlists.value,
      activeWatchlist: activeWatchlist.value,
      preferences: settingsValue(),
    });
  const fileInput = ref<HTMLInputElement>(),
    importType = ref('snapshot');
  function chooseImport(type: string) {
    importType.value = type;
    fileInput.value?.click();
  }
  async function importFile(event: Event) {
    const input = event.target as HTMLInputElement,
      file = input.files?.[0];
    if (!file || busy.value) return;
    busy.value = true;
    try {
      if (file.size > 40 * 1024 * 1024) throw Error('文件超过40MB。');
      const raw = JSON.parse(await file.text());
      let next = archive.value!,
        nextCaps = caps.value!,
        lists: Watchlist[] | undefined,
        active = '',
        prefs: Record<string, any> | undefined;
      if (importType.value === 'snapshot') next = validateSnapshot(raw, symbols.value);
      else if (importType.value === 'caps') nextCaps = validateCaps(raw, stocks.value);
      else {
        const backup = validateBackup(raw, assets.value);
        next = backup.snapshot;
        nextCaps = backup.caps;
        lists = backup.watchlists;
        active = backup.activeWatchlist;
        prefs = backup.preferences;
      }
      await persistScreeningData(account, next, nextCaps);
      archive.value = next;
      caps.value = nextCaps;
      imported.value = true;
      if (lists) {
        watchlists.value = lists;
        activeWatchlist.value = active;
      }
      if (prefs) applyPreferences(prefs);
      picked.value = [];
      storeSettings();
      notice.value = '导入完成，已重新计算方向与完整历史信号。';
    } catch (e) {
      notice.value = '导入未完成：' + (e as Error).message;
    } finally {
      busy.value = false;
      input.value = '';
    }
  }
  async function restoreArchive() {
    if (!archiveInfo.value) return;
    busy.value = true;
    try {
      await persistScreeningData(account, archiveInfo.value.snapshot, archiveInfo.value.caps);
      archive.value = archiveInfo.value.snapshot;
      caps.value = archiveInfo.value.caps;
      imported.value = false;
      notice.value = '已恢复平台归档行情，自选与筛选条件保留。';
    } catch (e) {
      notice.value = '恢复未完成：' + (e as Error).message;
    } finally {
      busy.value = false;
    }
  }

  const chartOpen = ref(false),
    profile = shallowRef<Security>(),
    symbol = ref(typeof initial.chart?.symbol === 'string' ? initial.chart.symbol : 'AAPL');
  const chartList = ref('');
  const chartQuery = ref(''),
    chartCategory = ref('all');
  const chartCategories = computed(() => [
    ...new Set(assets.value.map((s) => (s.kind === 'stock' ? s.sector : s.category))),
  ]);
  const pickerAssets = computed(() =>
    assets.value.filter(
      (s) =>
        (chartCategory.value === 'all' ||
          (s.kind === 'stock' ? s.sector : s.category) === chartCategory.value) &&
        `${s.symbol} ${s.name} ${s.english}`
          .toLowerCase()
          .includes(chartQuery.value.trim().toLowerCase()),
    ),
  );
  const cycleAssets = computed(() => rows.value.filter((s) => trends.value.has(s.symbol)));
  const frame = ref<Frame>(FRAMES.includes(initial.chart?.frame) ? initial.chart.frame : '1D'),
    signalAt = ref<number>();
  const groups = ref<System[]>(
    Array.isArray(initial.chart?.groups)
      ? SYSTEMS.filter((s) => initial.chart.groups.includes(s))
      : ['pma', 'zlma'],
  );
  const auxiliary = ref<Auxiliary[]>(
    Array.isArray(initial.chart?.auxiliary)
      ? AUXILIARIES.filter((s) => initial.chart.auxiliary.includes(s))
      : ['volume'],
  );
  const kalman = ref<KalmanOverlay[]>(
      KALMAN_OVERLAYS.filter((k) => initial.chart?.kalman?.includes(k)),
    ),
    kalmanPaint = ref<KalmanOverlay | 'none'>(
      KALMAN_OVERLAYS.includes(initial.chart?.kalmanPaint) ? initial.chart.kalmanPaint : 'none',
    );
  const range = ref([0, 60, 120, 250].includes(initial.chart?.range) ? initial.chart.range : 120),
    gridCharts = ref(initial.chart?.gridCharts === true),
    rolling = ref(initial.chart?.rolling !== false),
    levels = ref(initial.chart?.levels !== false);
  const selectedAsset = computed(() => assets.value.find((s) => s.symbol === symbol.value));
  function applyPreferences(prefs: Record<string, any>) {
    const filter = readFilterSettings(prefs);
    if (filter) changeTrend(filter.filters, filter.sort);
    if (typeof prefs.query === 'string') query.value = prefs.query;
    if (['all', 'stock', 'etf'].includes(prefs.kind)) kind.value = prefs.kind;
    if (['all', 'covered', 'holdings', 'sp500', 'ndx', 'curated'].includes(prefs.scope))
      scope.value = prefs.scope;
    if (Array.isArray(prefs.holdingSymbols))
      holdingSymbols.value = [
        ...new Set(
          prefs.holdingSymbols.filter(
            (s): s is string => typeof s === 'string' && symbols.value.includes(s),
          ),
        ),
      ];
    if (['all', 'bull', 'bear', 'conflict', 'short'].includes(prefs.structure))
      structure.value = prefs.structure;
    if (prefs.assetScreen) assetScreen.value = normalizeAsset(prefs.assetScreen);
    if (Array.isArray(prefs.presets))
      presets.value = prefs.presets
        .filter(
          (p) =>
            p &&
            typeof p.id === 'string' &&
            typeof p.name === 'string' &&
            p.name.trim() &&
            p.name.length <= 40 &&
            readFilterSettings(p),
        )
        .slice(0, 30);
    const chart = prefs.chart;
    if (!chart || typeof chart !== 'object') return;
    if (symbols.value.includes(chart.symbol)) symbol.value = chart.symbol;
    if (FRAMES.includes(chart.frame)) frame.value = chart.frame;
    if ([0, 60, 120, 250].includes(chart.range)) range.value = chart.range;
    if (Array.isArray(chart.groups)) groups.value = SYSTEMS.filter((s) => chart.groups.includes(s));
    if (Array.isArray(chart.auxiliary))
      auxiliary.value = AUXILIARIES.filter((s) => chart.auxiliary.includes(s));
    if (Array.isArray(chart.kalman))
      kalman.value = KALMAN_OVERLAYS.filter((s) => chart.kalman.includes(s));
    if (chart.kalmanPaint === 'none' || KALMAN_OVERLAYS.includes(chart.kalmanPaint))
      kalmanPaint.value = chart.kalmanPaint;
    if (typeof chart.rolling === 'boolean') rolling.value = chart.rolling;
    if (typeof chart.gridCharts === 'boolean') gridCharts.value = chart.gridCharts;
    if (typeof chart.levels === 'boolean') levels.value = chart.levels;
  }
  const chartFrames = computed(() => (gridCharts.value ? FRAMES : [frame.value]));
  const chartSeries = computed(() =>
    (archive.value?.series || []).map((source) => ({
      ...source,
      source:
        source.source || (imported.value ? '本地导入 · 未声明行情来源' : '分享包原生周期归档'),
    })),
  );
  const rollingSeries = computed(() =>
    archive.value && chartOpen.value && rolling.value && !signalAt.value
      ? (rollingMonitorSeries(
          {
            ...archive.value,
            series: chartSeries.value,
            sessionCalendar: archiveInfo.value?.calendar || [],
          },
          [symbol.value],
          Date.parse(archive.value.generatedAt),
        ) as SnapshotSeries[])
      : [],
  );
  function chartSource(f: Frame) {
    const native = chartSeries.value.find((s) => s.symbol === symbol.value && s.frame === f),
      local = rollingSeries.value.find((s) => s.frame === f);
    const closed = native?.bars.at(native.lastBarComplete === true ? -1 : -2);
    return local?.rolling && (!closed || local.rolling.asOf >= day(closed.t)) ? local : native;
  }
  const tvLink = (s: Security, f: Frame) =>
    `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(s.tv || s.symbol)}&interval=${
      f === 'M' ? '1M' : f
    }`;
  function openChart(s: string, f: Frame = frame.value, at?: number) {
    if (!symbols.value.includes(s)) return;
    symbol.value = s;
    frame.value = f;
    signalAt.value = at;
    chartOpen.value = true;
    if (!watchlists.value.some((list) => list.id === chartList.value))
      chartList.value = activeWatchlist.value || watchlists.value[0]?.id || '';
    void router.replace({
      query: { ...route.query, symbol: s, frame: f, at: at ? String(at) : undefined },
    });
  }
  function closeChart() {
    chartOpen.value = false;
    signalAt.value = undefined;
    void router.replace({
      query: { ...route.query, symbol: undefined, frame: undefined, at: undefined },
    });
  }
  function returnToLatest() {
    rolling.value = true;
    openChart(symbol.value, frame.value);
  }
  function stepAsset(delta: number) {
    const list = cycleAssets.value,
      index = list.findIndex((s) => s.symbol === symbol.value);
    if (list.length)
      openChart(
        list[
          index < 0
            ? delta < 0
              ? list.length - 1
              : 0
            : (index + delta + list.length) % list.length
        ].symbol,
        frame.value,
      );
  }
  function followRoute() {
    const s = String(route.query.symbol || '');
    if (!s) {
      chartOpen.value = false;
      return;
    }
    if (!symbols.value.includes(s)) {
      chartOpen.value = false;
      signalAt.value = undefined;
      return;
    }
    symbol.value = s;
    const f = String(route.query.frame) as Frame;
    frame.value = FRAMES.includes(f) ? f : '1D';
    const at = Number(route.query.at);
    signalAt.value = Number.isSafeInteger(at) && at > 0 && at < 10_000_000_000 ? at : undefined;
    chartOpen.value = true;
  }
  watch(() => [route.query.symbol, route.query.frame, route.query.at], followRoute);
  watch(
    [query, kind, scope, structure, activeWatchlist, assetScreen, trendFilters, sort],
    () => {
      page.value = 1;
      eventLimit.value = 100;
    },
    { deep: true },
  );
  watch([eventSystem, eventFrame, eventSide], () => {
    eventLimit.value = 100;
  });
  watch(
    kalman,
    () => {
      if (kalmanPaint.value !== 'none' && !kalman.value.includes(kalmanPaint.value))
        kalmanPaint.value = 'none';
    },
    { deep: true },
  );
  watch(
    [
      query,
      kind,
      scope,
      holdingSymbols,
      structure,
      activeWatchlist,
      assetScreen,
      trendFilters,
      sort,
      watchlists,
      presets,
      frame,
      symbol,
      range,
      groups,
      auxiliary,
      kalman,
      kalmanPaint,
      rolling,
      gridCharts,
      levels,
    ],
    storeSettings,
    { deep: true },
  );
  onMounted(load);
  onBeforeUnmount(() => controller?.abort());
</script>
<style src="./crossAsset/screening.css"></style>
