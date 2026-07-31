import { defineComponent, h, type PropType } from 'vue';

interface ReserveRankingRow {
  label: string;
  value: number;
  sublabel: string;
  detail?: string;
}

function formatNumber(value: number) {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
}

function formatSigned(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${formatNumber(value)}`;
}

export default defineComponent({
  name: 'ReserveRanking',
  props: {
    rows: {
      type: Array as PropType<ReserveRankingRow[]>,
      required: true,
    },
    color: {
      type: String,
      required: true,
    },
    diverging: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    return () => {
      const maxAbs = Math.max(...props.rows.map((row) => Math.abs(row.value)), 1);
      return h(
        'div',
        { class: 'reserve-module' },
        props.rows.map((row) => {
          const width = `${(Math.abs(row.value) / maxAbs) * 100}%`;
          const tone = props.diverging ? (row.value >= 0 ? '#148b6a' : '#dc2626') : props.color;
          return h('article', { key: `${row.label}-${row.value}`, class: 'reserve-module__item' }, [
            h('div', { class: 'reserve-module__header' }, [
              h('div', { class: 'reserve-module__title' }, [
                h('strong', row.label),
                h('span', row.sublabel),
              ]),
              row.detail ? h('span', { class: 'reserve-module__detail' }, row.detail) : null,
            ]),
            h('div', { class: 'reserve-module__track' }, [
              h('div', {
                class: 'reserve-module__fill',
                style: {
                  width,
                  backgroundColor: tone,
                  minWidth: props.diverging && row.value < 0 ? '12px' : undefined,
                },
              }),
            ]),
            h('div', { class: 'reserve-module__value' }, formatSigned(row.value) + ' 吨'),
          ]);
        }),
      );
    };
  },
});
